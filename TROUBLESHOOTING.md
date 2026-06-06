# TROUBLESHOOTING.md

## Quick Diagnosis

Run first: python platform/main.py health-check
Then check: logs/CERT_LIFECYCLE_YYYYMMDD_HHMMSS.log

---

## Authentication

Not logged in: az login --use-device-code
Wrong subscription: az account set --subscription "TGNA-PROD-C1"

## Key Vault Access

Cannot access vault causes:
- Not authenticated: az login --use-device-code
- Wrong sub: az account set --subscription "name"
- Missing RBAC: Request Key Vault Certificates Officer role
- IP Firewall: Ensure your IP is in vault allowlist (check VPN/VDI)

Diagnose: az keyvault show --name tgna-kv-king-ctrl --query properties.networkAcls

## Certificate Not Found

List certs: az keyvault certificate list --vault-name tgna-kv-king-ctrl

## Discovery - No Results

List vaults: az keyvault list --output table
Check sub: az account show

## Import Issues

PFX not found: Verify path exists
Import cancelled: Type exactly CONFIRM (case-sensitive) when prompted
PFX invalid: openssl pkcs12 -info -in king5.pfx -noout

## Validation Issues

HTTPS fails: curl -I https://king5.com
App Service not synced: Wait 5-10 min after KV import, then re-run validation

## Python Issues

ModuleNotFoundError: pip install -r requirements.txt
Config not found: cp config/settings.json.example config/settings.json

## PowerShell Issues

Module not found: Install-Module -Name Az -AllowClobber -Force -Scope CurrentUser
Execution policy: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

## OpenSSL Not Found

Windows: Download from https://slproweb.com/products/Win32OpenSSL.html
Add to PATH, restart terminal, verify: openssl version

## Quick Reference

| Error | Fix |
|---|---|
| AZURE LOGIN REQUIRED | az login --use-device-code |
| Cannot access Key Vault | Check IP allowlist and RBAC |
| Certificate not found | az keyvault certificate list |
| Import cancelled | Type CONFIRM exactly |
| ModuleNotFoundError | pip install -r requirements.txt |
| HTTPS check failed | curl -I https://hostname |

Attach logs/CERT_LIFECYCLE_*.log when escalating.
