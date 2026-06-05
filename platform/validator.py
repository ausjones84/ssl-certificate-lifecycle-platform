#!/usr/bin/env python3
"""platform/validator.py - Phase 5: Post-import validation (7-point check)."""

import os, ssl, socket, hashlib
from datetime import datetime, timezone
from platform.azure_client import AzureClient
from platform.logger import get_logger, log_pass, log_fail, log_summary


class ValidationResult:
    def __init__(self, name, passed=False, detail="", error=""):
        self.check_name = name
        self.passed = passed
        self.detail = detail
        self.error = error


class PostImportValidator:

    def __init__(self, client: AzureClient, logger=None):
        self.client = client
        self.log = logger or get_logger()
        self.results = []

    def validate(self, vault_name, cert_name, app_service_name="",
                 hostname="", expected_thumbprint="", resource_group=""):
        self.log.info("PHASE 5: POST-IMPORT VALIDATION | vault=%s cert=%s", vault_name, cert_name)
        self.results = []
        start = datetime.now()

        self._check1_cert_exists(vault_name, cert_name)
        self._check2_cert_enabled(vault_name, cert_name)
        self._check3_not_expired(vault_name, cert_name)
        self._check4_kv_status(vault_name)
        if app_service_name:
            self._check5_app_binding(app_service_name, resource_group)
        if hostname:
            self._check6_https_endpoint(hostname)
            self._check7_live_cert(hostname, expected_thumbprint)

        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        duration = (datetime.now() - start).total_seconds()
        log_summary(self.log, passed, failed, duration_s=duration)
        self._write_report(vault_name, cert_name, app_service_name, hostname)
        return self.results

    def _add(self, name, passed, detail="", error=""):
        r = ValidationResult(name, passed, detail, error)
        self.results.append(r)
        if passed: log_pass(self.log, name, detail)
        else: log_fail(self.log, name, error or detail)

    def _check1_cert_exists(self, vn, cn):
        cert = self.client.get_keyvault_certificate(vn, cn)
        self._add("Check 1: Certificate exists in Key Vault", cert is not None,
                  detail=f"version={cert.get('id','').split('/')[-1][:8]}" if cert else "",
                  error="Certificate not found" if not cert else "")

    def _check2_cert_enabled(self, vn, cn):
        cert = self.client.get_keyvault_certificate(vn, cn)
        if cert:
            enabled = cert.get("attributes", {}).get("enabled", False)
            self._add("Check 2: Certificate is enabled", enabled, detail=f"enabled={enabled}")
        else:
            self._add("Check 2: Certificate is enabled", False, error="Certificate not found")

    def _check3_not_expired(self, vn, cn):
        cert = self.client.get_keyvault_certificate(vn, cn)
        if cert:
            exp = cert.get("attributes", {}).get("expires")
            if exp:
                exp_dt = datetime.fromtimestamp(exp, tz=timezone.utc)
                days = (exp_dt - datetime.now(tz=timezone.utc)).days
                self._add("Check 3: Certificate not expired", days > 0,
                          detail=f"expires={exp_dt.strftime('%Y-%m-%d')} ({days}d)",
                          error=f"EXPIRED {abs(days)} days ago" if days <= 0 else "")
            else:
                self._add("Check 3: Certificate not expired", False, error="No expiry date found")
        else:
            self._add("Check 3: Certificate not expired", False, error="Certificate not found")

    def _check4_kv_status(self, vn):
        kv = self.client.run(["keyvault", "show", "--name", vn])
        if kv:
            state = kv.get("properties", {}).get("provisioningState", "Unknown")
            self._add("Check 4: Key Vault status OK", state == "Succeeded", detail=f"state={state}")
        else:
            self._add("Check 4: Key Vault status OK", False, error="Cannot query Key Vault")

    def _check5_app_binding(self, app_name, rg):
        bindings = self.client.get_app_service_ssl_bindings(app_name, rg)
        self._add("Check 5: App Service SSL binding exists", len(bindings) > 0,
                  detail=f"{len(bindings)} binding(s)", error="No SSL bindings found" if not bindings else "")

    def _check6_https_endpoint(self, hostname):
        try:
            import urllib.request
            ctx = ssl.create_default_context()
            req = urllib.request.Request(f"https://{hostname}", headers={"User-Agent": "CertPlatform/1.0"})
            with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
                self._add("Check 6: HTTPS endpoint reachable", resp.getcode() < 500,
                          detail=f"HTTP {resp.getcode()}")
        except Exception as e:
            self._add("Check 6: HTTPS endpoint reachable", False, error=str(e)[:100])

    def _check7_live_cert(self, hostname, expected_thumb):
        try:
            ctx = ssl.create_default_context()
            with socket.create_connection((hostname, 443), timeout=10) as sock:
                with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert_bytes = ssock.getpeercert(binary_form=True)
                    live_thumb = hashlib.sha1(cert_bytes).hexdigest()
                    self._add("Check 7: Live certificate presented", True,
                              detail=f"live_thumb={live_thumb[:16]}...")
        except Exception as e:
            self._add("Check 7: Live certificate check", False, error=str(e)[:100])

    def _write_report(self, vault_name, cert_name, app_svc, hostname):
        os.makedirs("reports", exist_ok=True)
        run_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)
        status = "PASSED" if passed == total else "FAILED"
        with open("reports/ValidationReport.md", "w", encoding="utf-8") as f:
            f.write(f"# Post-Import Validation Report\n\n")
            f.write(f"**Generated:** {run_date} | **Status:** {status} ({passed}/{total})\n\n")
            f.write(f"**Vault:** {vault_name} | **Certificate:** {cert_name}\n")
            if app_svc: f.write(f"**App Service:** {app_svc}\n")
            if hostname: f.write(f"**Hostname:** {hostname}\n")
            f.write("\n| Check | Result | Detail |\n|---|---|---|\n")
            for r in self.results:
                icon = "PASS" if r.passed else "FAIL"
                f.write(f"| {r.check_name} | {icon} | {r.detail or r.error} |\n")
        self.log.info("Validation report: reports/ValidationReport.md")

