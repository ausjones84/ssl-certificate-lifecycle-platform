#!/usr/bin/env python3
"""
platform/azure_client.py
=========================
Azure CLI wrapper with exponential-backoff retry logic.

All Azure CLI calls in the platform route through this module to ensure:
  - Consistent error handling
  - Automatic retry on transient failures (3 attempts, 2s/4s/8s backoff)
  - Structured logging of all CLI calls
  - Azure login validation before any operations
  - Subscription context management

Usage:
    from platform.azure_client import AzureClient
    client = AzureClient(logger=log)
    client.validate_login()
    result = client.run(["keyvault", "show", "--name", "my-kv"])
"""

import json
import logging
import os
import shutil
import subprocess
import sys
import time
from typing import Optional

# ---------------------------------------------------------------------------
# Azure CLI path resolution
# ---------------------------------------------------------------------------
_AZ_WINDOWS_FALLBACK = r"C:\Program Files (x86)\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"


def _resolve_az() -> str:
    """Find the Azure CLI executable, checking PATH then Windows fallback."""
    az = shutil.which("az")
    if az:
        return az
    if os.path.isfile(_AZ_WINDOWS_FALLBACK):
        return _AZ_WINDOWS_FALLBACK
    print("FATAL: Azure CLI not found.")
    print("  Install: https://aka.ms/installazurecliwindows")
    sys.exit(1)


AZ_CMD = _resolve_az()


class AzureClient:
    """
    Azure CLI wrapper with retry logic and authentication management.
    
    All methods return parsed JSON (dict/list) on success or None on failure.
    Errors are logged but not raised (caller checks for None return).
    """

    def __init__(self, logger: Optional[logging.Logger] = None, max_retries: int = 3):
        self.log = logger or logging.getLogger("cert_platform")
        self.max_retries = max_retries
        self._current_subscription: Optional[str] = None

    def run(self, args: list, timeout: int = 60) -> Optional[dict]:
        """
        Execute an Azure CLI command with retry logic.

        Args:
            args: CLI arguments (without 'az' prefix), e.g. ['keyvault', 'show', '--name', 'kv']
            timeout: Command timeout in seconds

        Returns:
            Parsed JSON response or None on failure
        """
        cmd = [AZ_CMD] + args + ["-o", "json"]
        self.log.debug("az %s", " ".join(args[:6]))

        for attempt in range(1, self.max_retries + 1):
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )
                if result.returncode == 0 and result.stdout.strip():
                    return json.loads(result.stdout)
                if result.returncode == 0 and not result.stdout.strip():
                    return {}  # Success with empty output (e.g., delete operations)
                # Non-zero return code
                err = (result.stderr or result.stdout or "Unknown error").strip()
                self.log.debug("az exit %d: %s", result.returncode, err[:200])
                if attempt < self.max_retries:
                    wait = 2 ** attempt
                    self.log.debug("Retry %d/%d in %ds", attempt, self.max_retries, wait)
                    time.sleep(wait)
            except subprocess.TimeoutExpired:
                self.log.debug("az timeout on attempt %d/%d", attempt, self.max_retries)
                if attempt < self.max_retries:
                    time.sleep(2 ** attempt)
            except json.JSONDecodeError as e:
                self.log.debug("JSON parse error: %s", e)
                return None
            except Exception as e:
                self.log.debug("az exception attempt %d/%d: %s", attempt, self.max_retries, e)
                if attempt < self.max_retries:
                    time.sleep(2 ** attempt)

        self.log.error("az command failed after %d attempts: az %s", self.max_retries, " ".join(args[:4]))
        return None

    def run_raw(self, args: list, timeout: int = 60) -> tuple:
        """
        Execute Azure CLI and return (returncode, stdout, stderr) directly.
        Use when you need the raw output rather than parsed JSON.
        """
        cmd = [AZ_CMD] + args
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return 1, "", "Command timed out"
        except Exception as e:
            return 1, "", str(e)

    def validate_login(self) -> dict:
        """
        Validate Azure CLI login. Exit with clear instructions if not authenticated.

        Returns:
            Account dict with user, tenant, subscription info
        """
        self.log.info("Validating Azure authentication...")
        result = self.run(["account", "show"], timeout=20)
        if result:
            user = result.get("user", {}).get("name", "unknown")
            tenant = result.get("tenantId", "unknown")
            sub = result.get("name", "unknown")
            self.log.info("  Authenticated as : %s", user)
            self.log.info("  Tenant           : %s", tenant)
            self.log.info("  Active sub       : %s", sub)
            self._current_subscription = sub
            return result

        self.log.error("=" * 60)
        self.log.error("AZURE LOGIN REQUIRED")
        self.log.error("=" * 60)
        self.log.error("")
        self.log.error("Run ONE of these commands and try again:")
        self.log.error("")
        self.log.error("  Interactive login:")
        self.log.error("    az login")
        self.log.error("")
        self.log.error("  Device code login (recommended for VDI/RDP):")
        self.log.error("    az login --use-device-code")
        self.log.error("")
        self.log.error("  Service principal:")
        self.log.error("    az login --service-principal -u <id> -p <secret> --tenant <tenant>")
        self.log.error("")
        self.log.error("After login, verify with: az account show")
        self.log.error("=" * 60)
        sys.exit(1)

    def set_subscription(self, subscription: str) -> bool:
        """Set the active Azure subscription."""
        rc, _, err = self.run_raw(["account", "set", "--subscription", subscription])
        if rc == 0:
            self._current_subscription = subscription
            self.log.debug("Subscription set: %s", subscription)
            return True
        self.log.error("Failed to set subscription '%s': %s", subscription, err[:200])
        return False

    def get_subscriptions(self) -> list:
        """List all accessible subscriptions."""
        result = self.run(["account", "list", "--query", "[].{name:name,id:id,state:state}"])
        return result or []

    def get_keyvault(self, vault_name: str, resource_group: str) -> Optional[dict]:
        """Get Key Vault details."""
        return self.run([
            "keyvault", "show",
            "--name", vault_name,
            "--resource-group", resource_group,
        ])

    def list_keyvault_certificates(self, vault_name: str) -> list:
        """List all certificates in a Key Vault."""
        result = self.run(["keyvault", "certificate", "list", "--vault-name", vault_name])
        return result or []

    def get_keyvault_certificate(self, vault_name: str, cert_name: str) -> Optional[dict]:
        """Get a specific certificate from Key Vault."""
        return self.run([
            "keyvault", "certificate", "show",
            "--vault-name", vault_name,
            "--name", cert_name,
        ])

    def import_keyvault_certificate(self, vault_name: str, cert_name: str, pfx_path: str, password: str = "") -> Optional[dict]:
        """
        Import a PFX certificate into Key Vault.
        NOTE: Caller is responsible for approval gate — never call directly.
        """
        args = [
            "keyvault", "certificate", "import",
            "--vault-name", vault_name,
            "--name", cert_name,
            "--file", pfx_path,
        ]
        if password:
            args += ["--password", password]
        return self.run(args, timeout=120)

    def list_app_services(self, resource_group: str = None) -> list:
        """List App Services, optionally filtered by resource group."""
        if resource_group:
            result = self.run(["webapp", "list", "--resource-group", resource_group])
        else:
            result = self.run(["webapp", "list"])
        return result or []

    def get_app_service_ssl_bindings(self, app_name: str, resource_group: str) -> list:
        """Get SSL bindings for an App Service."""
        result = self.run([
            "webapp", "config", "ssl", "list",
            "--resource-group", resource_group,
        ])
        if result:
            return [b for b in result if b.get("siteName") == app_name]
        return []

    def list_resource_groups(self) -> list:
        """List all resource groups in the current subscription."""
        result = self.run(["group", "list", "--query", "[].{name:name,location:location}"])
        return result or []

    def test_keyvault_access(self, vault_name: str) -> bool:
        """Test if the current identity can access a Key Vault."""
        result = self.run(["keyvault", "certificate", "list", "--vault-name", vault_name])
        return result is not None

