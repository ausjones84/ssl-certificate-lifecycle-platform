# OPERATIONS_GUIDE.md

## Daily Operations

### Morning Checks

1. Run risk analysis to check for any newly-critical certificates:

    python platform/main.py ai-report --days 30

2. Review the output for any CRITICAL or HIGH risk certificates.

3. If any critical certs found, generate Jira update:

    python platform/main.py jira-update --cert [cert-name] --stage risk-identified

### Weekly Operations

Every Monday, run a full discovery scan:

    python platform/main.py discover --subscription "TGNA-PROD-C1"
    python platform/main.py ai-report --days 90

This updates the inventory and identifies any certs entering the 90-day renewal window.

---

## Certificate Renewal Workflow

### Standard Renewal (Step-by-Step)

1. Check discovery output for expiring certificate
2. Generate Jira update:
       python platform/main.py jira-update --cert king-wildcard --stage renewal-started
3. Generate CSR:
       .\scripts\csr\New-CertificateRequest.ps1 -CommonName "*.king5.com"
4. Submit CSR to Sectigo portal (manual step)
5. Complete domain validation in Sectigo (manual step)
6. Download certificate files from Sectigo
7. Build chain and create PFX:
       .\scripts\processing\Build-CertificateChain.ps1 -CertPath C:\certs\king5.cer
       .\scripts\processing\New-PfxPackage.ps1 -CertPath C:\certs\king5.cer -KeyPath C:\certs\king5.key
8. Preview the import:
       python platform/main.py import --cert king-wildcard --pfx C:\certs\king5.pfx --preview
9. Dry run:
       python platform/main.py import --cert king-wildcard --pfx C:\certs\king5.pfx --dry-run
10. Execute import (with CONFIRM approval):
       python platform/main.py import --cert king-wildcard --pfx C:\certs\king5.pfx --execute
11. Validate:
       python platform/main.py validate --cert king-wildcard --hostname king5.com
12. Update Jira:
       python platform/main.py jira-update --cert king-wildcard --stage renewal-complete

---

## SLA Targets

| Risk Level | Days Until Expiry | Target Renewal Start | Target Completion |
|---|---|---|---|
| CRITICAL | <= 14 days | Immediately | Within 48 hours |
| HIGH | 15-30 days | Same day | Within 5 business days |
| MEDIUM | 31-60 days | This week | Within 2 weeks |
| LOW | 61-90 days | Within 2 weeks | Before 30-day threshold |

---

## Emergency Certificate Renewal

If a certificate has expired or will expire within 24 hours:

1. Immediately generate Jira update:
       python platform/main.py jira-update --cert [cert] --stage risk-identified
2. Escalate to manager and security team
3. Contact Sectigo for emergency certificate issuance
4. Follow standard renewal steps 3-12 above at emergency pace
5. Notify stakeholders of potential service impact

See docs/runbooks/emergency-cert-runbook.md for full emergency procedure.

---

## Log Management

Logs are written to logs/CERT_LIFECYCLE_YYYYMMDD_HHMMSS.log

Log retention: Logs accumulate in logs/. Archive or delete files older than 90 days:

    # PowerShell
    Get-ChildItem logs/ | Where-Object { $_.CreationTime -lt (Get-Date).AddDays(-90) } | Remove-Item

Log levels:
- DEBUG: verbose tracing (file only)
- INFO: normal operations (console + file)
- WARNING: attention needed (console + file)
- ERROR: operation failed (console + file)

---

## Report Management

Reports are generated to reports/ directory.

The CertificateInventory.json is the primary data source for the dashboard.
Run a new discovery to refresh it:

    python platform/main.py discover

Then reload dashboard/index.html to see updated data.

---

## Key Contacts and Escalation

Update this section with your team's contact information:

| Role | Responsibility |
|---|---|
| Platform Owner | [Name/Team] |
| Azure Operations | [Name/Team] |
| Security Team | [Name/Team] |
| Sectigo Contact | [Account Manager] |

---

## Change Management

All Key Vault imports must follow the approval workflow:
1. Preview to review proposed changes
2. Dry-run to validate without changes
3. Raise change request if required by your CAB process
4. Execute with CONFIRM during the approved change window
5. Validate and attach ValidationReport.md to change ticket
6. Update Jira ticket with completion status# Operations Guide

**SSL Certificate Lifecycle Management Platform**

---

## Operational Overview

This guide covers day-to-day operations, scheduled procedures, emergency response,
and maintenance tasks for the SSL Certificate Lifecycle Platform.

---

## Scheduled Operations

### Weekly Certificate Discovery
Run every Monday to refresh the certificate inventory:
```bash
python platform/main.py discover
python platform/main.py ai-report
python platform/main.py report
```

Or trigger the Azure DevOps scheduled pipeline:
`pipelines/azure-pipelines-cert-discovery.yml`

### Monthly Risk Review
1. Run full discovery
2. Review `reports/RiskReport.md` for certificates expiring within 90 days
3. Create Jira tickets for all at-risk certificates
4. Assign renewal work to engineers

---

## Certificate Renewal Procedure

### Step 1: Identify Expiring Certificate
```bash
python platform/main.py discover
python platform/main.py ai-report
```
Review `reports/RiskReport.md`.

### Step 2: Generate CSR
```powershell
.\scripts\csr\New-CertificateRequest.ps1 -Domain "example.com" -SANs "www.example.com"
```

### Step 3: Submit to CA
Submit the `.csr` file to Sectigo (or your CA).
Complete DNS or HTTP domain validation.
Download the signed certificate files.

### Step 4: Build Chain and PFX
```powershell
.\scripts\processing\Build-CertificateChain.ps1 -CertPath ".\certs\example.com.crt" -IntermediatePath ".\certs\intermediate.crt"
.\scripts\processing\New-PfxPackage.ps1 -ChainPath ".\certs\chain.crt" -KeyPath ".\certs\example.com.key" -OutputPath ".\certs\example.com.pfx"
```

### Step 5: Preview Import
```powershell
.\scripts\keyvault\Import-CertificateToKeyVault.ps1 -VaultName "your-kv" -CertName "your-cert" -PfxPath ".\certs\example.com.pfx" -Preview
```
Review preview output. Confirm all values are correct.

### Step 6: Execute Import
```powershell
.\scripts\keyvault\Import-CertificateToKeyVault.ps1 -VaultName "your-kv" -CertName "your-cert" -PfxPath ".\certs\example.com.pfx" -Execute
```
Type `CONFIRM` when prompted.

### Step 7: Validate
```powershell
.\scripts\validation\Invoke-PostImportValidation.ps1 -VaultName "your-kv" -CertName "your-cert" -AppServiceName "your-app"
```
Review `reports/ValidationReport.md`. All 7 checks must pass.

### Step 8: Update Jira
```bash
python platform/main.py jira-update --event renewal-complete --ticket CERT-123
```

---

## Emergency Certificate Replacement

If a certificate has expired or is presenting errors:

1. Notify stakeholders immediately
2. Run emergency CSR generation
3. Contact CA for expedited certificate issuance
4. Complete chain build and PFX generation
5. Execute import with CONFIRM approval
6. Validate within 15 minutes of import
7. Confirm HTTPS endpoint is live
8. Update Jira with resolution details

See `docs/runbooks/emergency-cert-runbook.md` for the full emergency runbook.

---

## Monitoring and Alerting

### Dashboard
Open `dashboard/index.html` for a live view of certificate status.
Refresh weekly after discovery runs.

### Email Notifications
Configure `notifications` section in `config/settings.json` to receive alerts
for certificates expiring within 30 days.

### Pipeline Alerts
Azure DevOps pipelines notify the configured email on failure.

---

## Log Management

Logs are stored in `logs/` with format `CERT_LIFECYCLE_YYYYMMDD_HHMMSS.log`.
Retain logs for 90 days minimum.
Archive logs monthly to long-term storage.

---

## Access Control

Minimum required Azure RBAC roles:
- Key Vault Certificate Officer (or Secrets Officer)
- App Service Contributor (for binding validation)
- Reader on all resource groups containing App Services

---

## Backup Procedures

Certificate artifacts (PFX files) should be stored in a secure location outside this repository.
Key Vault automatically versions all certificates — no separate backup required for Key Vault.

---

## Maintenance

### Update Python Dependencies
```bash
pip install --upgrade -r requirements.txt
```

### Update Azure CLI
```bash
az upgrade
```

### Update Az PowerShell Module
```powershell
Update-Module -Name Az
```
