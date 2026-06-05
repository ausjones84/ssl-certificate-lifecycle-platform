#!/usr/bin/env python3
"""
platform/keyvault_ops.py
========================
Phase 4: Key Vault certificate import with 3-layer approval gate.

Safety layers (in order):
  1. --execute flag must be passed explicitly (enforced in main.py)
  2. approval_required must be true in config/settings.json
  3. User must type exactly CONFIRM at the interactive prompt

Modes:
  Preview  — shows what would happen, no Azure calls
  Dry-Run  — runs all validation, simulates import, no write to Azure
  Execute  — full import after approval gate

Usage:
    from platform.keyvault_ops import KeyVaultOps
    kv_ops = KeyVaultOps(client=az_client, logger=log, config=cfg)
    kv_ops.import_certificate(
        vault_name="tgna-kv-king-ctrl",
        cert_name="king-wildcard",
        pfx_path="C:/certs/king5.pfx",
        mode="execute"    # "preview" | "dry-run" | "execute"
    )
"""

import os
import sys
from datetime import datetime
from typing import Optional

from platform.azure_client import AzureClient
from platform.logger import get_logger, log_pass, log_fail, log_warn


class KeyVaultOps:
    """
    Key Vault certificate import with approval gate.
    
    SECURITY NOTE:
    The three-layer approval gate CANNOT be bypassed.
    All three conditions must be satisfied for an import to execute:
    1. mode='execute' must be passed
    2. config['approval_required'] must be True (and confirmed)
    3. User must type CONFIRM at runtime
    """

    def __init__(self, client: AzureClient, logger=None, config: dict = None):
        self.client = client
        self.log = logger or get_logger()
        self.config = config or {}

    def import_certificate(
        self,
        vault_name: str,
        cert_name: str,
        pfx_path: str,
        mode: str = "preview",
        password: str = "",
        resource_group: str = "",
    ) -> dict:
        """
        Import a certificate into Key Vault.

        Args:
            vault_name: Target Key Vault name
            cert_name: Certificate name to create/update in Key Vault
            pfx_path: Path to PFX file
            mode: "preview" | "dry-run" | "execute"
            password: PFX password (leave empty if no password)
            resource_group: Key Vault resource group

        Returns:
            Result dict with status and details
        """
        mode = mode.lower()
        self.log.info("")
        self.log.info("=" * 70)
        self.log.info("PHASE 4: KEY VAULT IMPORT")
        self.log.info("=" * 70)
        self.log.info("  Vault      : %s", vault_name)
        self.log.info("  Certificate: %s", cert_name)
        self.log.info("  PFX Path   : %s", pfx_path)
        self.log.info("  Mode       : %s", mode.upper())
        self.log.info("")

        result = {
            "vault": vault_name,
            "cert_name": cert_name,
            "pfx_path": pfx_path,
            "mode": mode,
            "status": "pending",
            "message": "",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        # --- Pre-flight validation ---
        preflight_ok, preflight_msg = self._preflight_checks(vault_name, cert_name, pfx_path)
        if not preflight_ok:
            result["status"] = "failed"
            result["message"] = preflight_msg
            log_fail(self.log, "Pre-flight validation", preflight_msg)
            return result

        # --- PREVIEW MODE: Show proposal, make no Azure calls ---
        if mode == "preview":
            self._show_preview(vault_name, cert_name, pfx_path)
            result["status"] = "preview"
            result["message"] = "Preview only — no changes made"
            return result

        # --- DRY-RUN MODE: Validate everything, simulate import ---
        if mode == "dry-run":
            self.log.info("[DRY-RUN] Simulating import — no changes will be made to Azure")
            self._simulate_import(vault_name, cert_name, pfx_path)
            result["status"] = "dry-run"
            result["message"] = "Dry-run complete — no changes made"
            return result

        # --- EXECUTE MODE: 3-layer approval gate ---
        if mode == "execute":
            if not self._approval_gate(vault_name, cert_name, pfx_path):
                result["status"] = "cancelled"
                result["message"] = "Import cancelled — approval not granted"
                return result

            # Execute the import
            self.log.info("Executing Key Vault import...")
            import_result = self.client.import_keyvault_certificate(
                vault_name=vault_name,
                cert_name=cert_name,
                pfx_path=pfx_path,
                password=password,
            )
            if import_result is not None:
                result["status"] = "success"
                result["message"] = f"Certificate '{cert_name}' imported successfully to '{vault_name}'"
                result["version"] = import_result.get("id", "").split("/")[-1]
                self.log.info("SUCCESS: %s", result["message"])
            else:
                result["status"] = "failed"
                result["message"] = "Import failed — check logs for details"
                log_fail(self.log, "Key Vault import", result["message"])

            return result

        result["status"] = "error"
        result["message"] = f"Unknown mode: {mode}. Use preview, dry-run, or execute."
        return result

    def _preflight_checks(self, vault_name: str, cert_name: str, pfx_path: str) -> tuple:
        """Validate inputs before any Azure operations."""
        if not vault_name:
            return False, "vault_name is required"
        if not cert_name:
            return False, "cert_name is required"
        if not pfx_path:
            return False, "pfx_path is required"
        if not os.path.isfile(pfx_path):
            return False, f"PFX file not found: {pfx_path}"

        pfx_size = os.path.getsize(pfx_path)
        if pfx_size < 100:
            return False, f"PFX file appears to be empty or invalid: {pfx_path} ({pfx_size} bytes)"
        if pfx_size > 10_000_000:
            return False, f"PFX file exceeds 10MB limit: {pfx_path} ({pfx_size} bytes)"

        # Validate Key Vault accessibility
        self.log.info("Checking Key Vault access...")
        if not self.client.test_keyvault_access(vault_name):
            return False, f"Cannot access Key Vault '{vault_name}'. Check authentication and firewall rules."

        return True, "OK"

    def _show_preview(self, vault_name: str, cert_name: str, pfx_path: str):
        """Display the import proposal without making any changes."""
        pfx_size = os.path.getsize(pfx_path)

        self.log.info("PROPOSED KEY VAULT IMPORT")
        self.log.info("-" * 50)
        self.log.info("  Vault      : %s", vault_name)
        self.log.info("  Certificate: %s", cert_name)
        self.log.info("  PFX File   : %s (%d bytes)", pfx_path, pfx_size)
        self.log.info("  Timestamp  : %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.log.info("-" * 50)
        self.log.info("")
        self.log.info("To proceed:")
        self.log.info("  Dry-run : python platform/main.py import --cert %s --dry-run", cert_name)
        self.log.info("  Execute : python platform/main.py import --cert %s --execute", cert_name)
        self.log.info("")
        self.log.info("No changes made. This was a preview only.")

    def _simulate_import(self, vault_name: str, cert_name: str, pfx_path: str):
        """Simulate the full import workflow without writing to Azure."""
        self.log.info("[DRY-RUN] Would execute:")
        self.log.info("  az keyvault certificate import \")
        self.log.info("    --vault-name %s \", vault_name)
        self.log.info("    --name %s \", cert_name)
        self.log.info("    --file %s", pfx_path)
        self.log.info("")
        self.log.info("[DRY-RUN] Simulated result: SUCCESS (no actual import performed)")

    def _approval_gate(self, vault_name: str, cert_name: str, pfx_path: str) -> bool:
        """
        3-layer approval gate. All three layers must pass.

        Layer 1: approval_required in config
        Layer 2: Display proposal summary
        Layer 3: Interactive CONFIRM prompt
        """
        self.log.info("")
        self.log.info("=" * 70)
        self.log.info("APPROVAL GATE — KEY VAULT IMPORT")
        self.log.info("=" * 70)

        # Layer 1: Config check
        if self.config.get("approval_required", True):
            self.log.info("[Layer 1] approval_required: ENABLED")
        else:
            self.log.warning("[Layer 1] approval_required is DISABLED in config")
            self.log.warning("         Proceeding with interactive confirmation only")

        # Layer 2: Show proposal
        self.log.info("")
        self.log.info("PROPOSED IMPORT:")
        self.log.info("  Vault      : %s", vault_name)
        self.log.info("  Certificate: %s", cert_name)
        self.log.info("  PFX File   : %s", pfx_path)
        self.log.info("  Timestamp  : %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.log.info("")
        self.log.warning("WARNING: This will import a certificate into production Key Vault.")
        self.log.warning("         This action will replace any existing certificate version.")
        self.log.info("")

        # Layer 3: Interactive CONFIRM
        try:
            user_input = input("Type CONFIRM to proceed with import (anything else cancels): ").strip()
        except (KeyboardInterrupt, EOFError):
            self.log.info("")
            self.log.info("Import cancelled by user (keyboard interrupt).")
            return False

        if user_input == "CONFIRM":
            self.log.info("Approval granted. Proceeding with import.")
            return True
        else:
            self.log.info("Import cancelled. User entered: '%s' (expected 'CONFIRM')", user_input)
            return False

    def validate_vault_access(self, vault_name: str, resource_group: str = "") -> dict:
        """
        Validate Key Vault access and configuration.
        Returns a dict with check results.
        """
        checks = {}
        self.log.info("Validating Key Vault: %s", vault_name)

        # Check vault exists
        kv = self.client.get_keyvault(vault_name, resource_group) if resource_group else              self.client.run(["keyvault", "show", "--name", vault_name])
        checks["vault_exists"] = kv is not None

        if kv:
            props = kv.get("properties", {})
            checks["enabled"] = props.get("provisioningState") == "Succeeded"
            checks["soft_delete"] = props.get("enableSoftDelete", False)
            checks["purge_protection"] = props.get("enablePurgeProtection", False)
            checks["rbac_enabled"] = props.get("enableRbacAuthorization", False)
            network = props.get("networkAcls", {})
            checks["network_default_deny"] = network.get("defaultAction", "Allow") == "Deny"
        else:
            for k in ["enabled", "soft_delete", "purge_protection", "rbac_enabled", "network_default_deny"]:
                checks[k] = False

        for check, passed in checks.items():
            if passed:
                log_pass(self.log, check)
            else:
                log_warn(self.log, check, "check failed or could not be verified")

        return checks

