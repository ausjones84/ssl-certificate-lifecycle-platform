#!/usr/bin/env python3
"""
platform/discovery.py
=====================
Phase 1: Automated SSL certificate discovery across Azure subscriptions.

Discovers:
  - All App Services and their SSL bindings
  - All Key Vaults and their certificate objects
  - Certificate expiration dates
  - Certificate versions
  - App Service <-> Key Vault <-> Secret mappings
  - Resource groups and environments

Outputs passed to inventory.py for report generation.

Usage:
    from platform.discovery import CertificateDiscovery
    discoverer = CertificateDiscovery(client=az_client, logger=log, config=cfg)
    inventory = discoverer.run(subscription="TGNA-PROD-C1")
"""

import json
import os
from datetime import datetime, timezone
from typing import Optional

from platform.azure_client import AzureClient
from platform.logger import get_logger


class CertificateRecord:
    """Represents a single discovered certificate with all metadata."""

    def __init__(self):
        self.domain: str = ""
        self.cert_name: str = ""
        self.key_vault: str = ""
        self.secret_name: str = ""
        self.resource_group: str = ""
        self.subscription: str = ""
        self.app_service: str = ""
        self.expiration: Optional[datetime] = None
        self.thumbprint: str = ""
        self.issuer: str = ""
        self.subject: str = ""
        self.version: str = ""
        self.enabled: bool = True
        self.days_until_expiry: Optional[int] = None
        self.risk_level: str = "UNKNOWN"
        self.binding_status: str = "UNKNOWN"
        self.last_checked: str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.notes: str = ""

    def calculate_risk(self):
        """Calculate risk level based on days until expiry."""
        if self.days_until_expiry is None:
            self.risk_level = "UNKNOWN"
        elif self.days_until_expiry < 0:
            self.risk_level = "EXPIRED"
        elif self.days_until_expiry <= 14:
            self.risk_level = "CRITICAL"
        elif self.days_until_expiry <= 30:
            self.risk_level = "HIGH"
        elif self.days_until_expiry <= 60:
            self.risk_level = "MEDIUM"
        elif self.days_until_expiry <= 90:
            self.risk_level = "LOW"
        else:
            self.risk_level = "OK"

    def to_dict(self) -> dict:
        return {
            "domain": self.domain,
            "cert_name": self.cert_name,
            "key_vault": self.key_vault,
            "secret_name": self.secret_name,
            "resource_group": self.resource_group,
            "subscription": self.subscription,
            "app_service": self.app_service,
            "expiration": self.expiration.strftime("%Y-%m-%d") if self.expiration else "Unknown",
            "thumbprint": self.thumbprint,
            "issuer": self.issuer,
            "subject": self.subject,
            "version": self.version,
            "enabled": self.enabled,
            "days_until_expiry": self.days_until_expiry,
            "risk_level": self.risk_level,
            "binding_status": self.binding_status,
            "last_checked": self.last_checked,
            "notes": self.notes,
        }


class CertificateDiscovery:
    """
    Discovers SSL certificates across Azure subscriptions.
    
    Discovery flow:
    1. Validate Azure login
    2. List resource groups in subscription(s)
    3. Discover Key Vaults and their certificates
    4. Discover App Services and their SSL bindings
    5. Map certificates to App Services
    6. Calculate expiry and risk levels
    7. Return list of CertificateRecord objects
    """

    def __init__(self, client: AzureClient, logger=None, config: dict = None):
        self.client = client
        self.log = logger or get_logger()
        self.config = config or {}
        self.records: list = []

    def run(
        self,
        subscription: str = None,
        all_subscriptions: bool = False,
        resource_group: str = None,
    ) -> list:
        """
        Execute the discovery scan.

        Args:
            subscription: Specific subscription name to scan
            all_subscriptions: Scan all accessible subscriptions
            resource_group: Limit scan to specific resource group

        Returns:
            List of CertificateRecord objects
        """
        self.log.info("=" * 70)
        self.log.info("PHASE 1: CERTIFICATE DISCOVERY")
        self.log.info("=" * 70)
        start = datetime.now()
        self.records = []

        # Resolve subscriptions to scan
        if all_subscriptions:
            subs = self.client.get_subscriptions()
            sub_names = [s["name"] for s in subs if s.get("state") == "Enabled"]
            self.log.info("Scanning %d subscriptions", len(sub_names))
        elif subscription:
            sub_names = [subscription]
        else:
            # Use current context
            account = self.client.run(["account", "show"])
            sub_names = [account.get("name", "unknown")] if account else []

        for sub in sub_names:
            self.log.info("")
            self.log.info("Subscription: %s", sub)
            if not self.client.set_subscription(sub):
                self.log.warning("  Cannot access subscription '%s' — skipping", sub)
                continue
            self._discover_subscription(sub, resource_group)

        # Calculate risk levels
        for record in self.records:
            record.calculate_risk()

        duration = (datetime.now() - start).total_seconds()
        self.log.info("")
        self.log.info("=" * 70)
        self.log.info("DISCOVERY COMPLETE")
        self.log.info("  Certificates found : %d", len(self.records))
        self.log.info("  Duration           : %.1fs", duration)
        self._log_risk_summary()
        self.log.info("=" * 70)

        return self.records

    def _discover_subscription(self, sub: str, resource_group_filter: str = None):
        """Discover certificates in a single subscription."""

        # Get resource groups
        if resource_group_filter:
            rgs = [{"name": resource_group_filter}]
        else:
            rgs = self.client.list_resource_groups()
            self.log.info("  Resource groups: %d", len(rgs))

        # Discover Key Vaults
        kv_records = {}
        for rg in rgs:
            rg_name = rg["name"]
            kvs = self.client.run([
                "keyvault", "list",
                "--resource-group", rg_name,
                "--query", "[].{name:name,uri:properties.vaultUri}",
            ]) or []

            for kv in kvs:
                kv_name = kv.get("name", "")
                self.log.info("  Key Vault: %s (RG: %s)", kv_name, rg_name)
                certs = self.client.list_keyvault_certificates(kv_name)

                for cert_item in certs:
                    cert_name = cert_item.get("name", "")
                    self.log.debug("    Certificate: %s", cert_name)

                    # Get full certificate details
                    cert_detail = self.client.get_keyvault_certificate(kv_name, cert_name)
                    if not cert_detail:
                        continue

                    record = CertificateRecord()
                    record.cert_name = cert_name
                    record.key_vault = kv_name
                    record.resource_group = rg_name
                    record.subscription = sub
                    record.enabled = cert_item.get("attributes", {}).get("enabled", True)
                    record.version = cert_detail.get("id", "").split("/")[-1][:8]

                    # Parse expiration
                    exp_epoch = cert_item.get("attributes", {}).get("expires")
                    if exp_epoch:
                        try:
                            record.expiration = datetime.fromtimestamp(exp_epoch, tz=timezone.utc)
                            now = datetime.now(tz=timezone.utc)
                            record.days_until_expiry = (record.expiration - now).days
                        except Exception:
                            pass

                    # Parse certificate policy for subject/issuer
                    policy = cert_detail.get("policy", {})
                    x509 = policy.get("x509CertificateProperties", {})
                    record.subject = x509.get("subject", "")
                    record.domain = record.subject.replace("CN=", "").strip()
                    record.issuer = policy.get("issuerParameters", {}).get("name", "")

                    # Parse thumbprint from secret
                    secret_props = cert_detail.get("x509Thumbprint", "")
                    record.thumbprint = secret_props[:16] + "..." if len(secret_props) > 16 else secret_props

                    kv_records[cert_name] = record

        self.records.extend(kv_records.values())

        # Discover App Services and map SSL bindings
        app_services = self.client.list_app_services()
        self.log.info("  App Services: %d", len(app_services))

        for app in app_services:
            app_name = app.get("name", "")
            app_rg = app.get("resourceGroup", "")

            bindings = self.client.get_app_service_ssl_bindings(app_name, app_rg)
            for binding in bindings:
                thumbprint = binding.get("thumbprint", "")
                # Try to match binding thumbprint to discovered certificate
                for record in self.records:
                    if thumbprint and thumbprint[:8].lower() in record.thumbprint.lower():
                        record.app_service = app_name
                        record.binding_status = "BOUND"
                        break

    def _log_risk_summary(self):
        """Log risk level counts."""
        risk_counts = {}
        for r in self.records:
            risk_counts[r.risk_level] = risk_counts.get(r.risk_level, 0) + 1

        for level in ["EXPIRED", "CRITICAL", "HIGH", "MEDIUM", "LOW", "OK", "UNKNOWN"]:
            count = risk_counts.get(level, 0)
            if count:
                self.log.info("  %-10s: %d", level, count)

