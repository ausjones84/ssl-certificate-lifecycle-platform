# QUICKSTART.md — Be Operational in Under 10 Minutes

This guide gets you from zero to running your first certificate discovery in under 10 minutes. It assumes you have completed INSTALL.md.

---

## Minute 1-2: Clone and Configure

```bash
git clone https://github.com/ausjones84/ssl-certificate-lifecycle-platform.git
cd ssl-certificate-lifecycle-platform
pip install -r requirements.txt
cp config/settings.json.example config/settings.json
```

Open config/settings.json and set at minimum:
- subscription_id
- tenant_id  
- key_vault_name (e.g., tgna-kv-king-ctrl)
- resource_group

## Minute 3: Authenticate

```bash
az login --use-device-code
az account set --subscription "your-subscription-name"
```

## Minute 4: Run Health Check

```bash
python platform/main.py health-check
```

All checks should show [PASS]. If any fail, see TROUBLESHOOTING.md.

## Minute 5: Discover All Certificates

```bash
python platform/main.py discover --subscription "your-subscription"
```

This scans your Azure environment and produces:
- reports/CertificateInventory.csv
- reports/CertificateInventory.json
- reports/CertificateInventory.md

## Minute 6: View Your Inventory

```bash
cat reports/CertificateInventory.md
```

Example output:
```
# Certificate Inventory
Generated: 2026-06-05 10:00:00

| Domain | Certificate | Key Vault | App Service | Expires | Days Left | Status |
|---|---|---|---|---|---|---|
| *.king5.com | king-wildcard | tgna-kv-king-ctrl | interactive-king5 | 2026-06-09 | 4 | CRITICAL |
```

## Minute 7: Run AI Risk Report

```bash
python platform/main.py ai-report --days 90
```

Example output:
```
CERTIFICATE RISK ANALYSIS
==========================

CRITICAL (< 30 days):
  king-wildcard — expires in 4 days
  App Service: interactive-king5
  Key Vault: tgna-kv-king-ctrl
  ACTION REQUIRED: Renew immediately.

```

## Minute 8: Preview a Key Vault Import (No Changes Made)

```bash
python platform/main.py import --cert king-wildcard --preview
```

Preview shows exactly what would happen — no changes made to Azure.

## Minute 9: View the Dashboard

Open dashboard/index.html in your browser. No server required.

The dashboard shows:
- Certificates expiring in 30/60/90 days
- Failed validations
- Key Vault status
- App Service synchronization

## Minute 10: Generate a Jira Update

```bash
python platform/main.py jira-update --cert king-wildcard --stage discovery-complete
```

Outputs a ready-to-paste Jira ticket update.

---

## Common Commands Reference

```bash
# Discovery
python platform/main.py discover --subscription "sub-name"
python platform/main.py discover --all-subscriptions

# AI analysis
python platform/main.py ai-report --days 30
python platform/main.py ai-report --days 60
python platform/main.py ai-report --days 90
python platform/main.py executive-summary
python platform/main.py engineer-summary

# Key Vault import (always preview first)
python platform/main.py import --cert king-wildcard --preview
python platform/main.py import --cert king-wildcard --dry-run
python platform/main.py import --cert king-wildcard --execute

# Validation
python platform/main.py validate --cert king-wildcard
python platform/main.py validate --all

# Jira updates
python platform/main.py jira-update --cert king-wildcard --stage discovery-complete
python platform/main.py jira-update --cert king-wildcard --stage renewal-complete
python platform/main.py jira-update --cert king-wildcard --stage validation-complete

# Reporting
python platform/main.py report --format all
python platform/main.py report --format html
python platform/main.py report --format csv

# Health check
python platform/main.py health-check
```

## PowerShell Commands Reference

```powershell
# Discovery
.\scripts\discovery\Invoke-CertificateDiscovery.ps1 -SubscriptionId "your-sub-id"

# CSR generation
.\scripts\csr\New-CertificateRequest.ps1 -CommonName "*.king5.com" -OutputPath "C:\certs"

# PFX packaging
.\scripts\processing\New-PfxPackage.ps1 -CertPath "C:\certs\king5.cer" -KeyPath "C:\certs\king5.key"

# Key Vault import
.\scripts\keyvault\Import-CertificateToKeyVault.ps1 -VaultName "tgna-kv-king-ctrl" -CertName "king-wildcard" -PfxPath "C:\certs\king5.pfx" -Preview

# Post-import validation
.\scripts\validation\Invoke-PostImportValidation.ps1 -VaultName "tgna-kv-king-ctrl" -CertName "king-wildcard" -AppServiceName "interactive-king5"
```

---

## What To Do If Something Fails

1. Run health-check: `python platform/main.py health-check`
2. Check the log file: `logs/CERT_LIFECYCLE_YYYYMMDD_HHMMSS.log`
3. See TROUBLESHOOTING.md
4. Check Azure auth: `az account show`
5. Check Key Vault firewall: ensure your IP is allowed

---

Next: See USER_GUIDE.md for the complete operational guide.
