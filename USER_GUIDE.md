# User Guide

**SSL Certificate Lifecycle Management Platform**

---

## Getting Started

Before using the platform, ensure you have completed the steps in `INSTALL.md`.

Verify your setup:
```bash
python platform/main.py health-check
```

---

## Phase 1: Discover Certificates

### Python (recommended)
```bash
python platform/main.py discover
```

This scans all App Services and Key Vaults in your Azure subscription and generates:
- `reports/CertificateInventory.csv`
- `reports/CertificateInventory.json`
- `reports/CertificateInventory.md`

### PowerShell
```powershell
.\scripts\discovery\Invoke-CertificateDiscovery.ps1
```

---

## Phase 2: Generate a CSR

### Python
```bash
python platform/main.py csr --domain example.com --san "www.example.com,api.example.com"
```

### PowerShell
```powershell
.\scripts\csr\New-CertificateRequest.ps1 -Domain "example.com" -SANs "www.example.com,api.example.com"
```

CSR and private key are saved to `csr/` directory (excluded from git).
Submit the `.csr` file to Sectigo or your CA.

---

## Phase 3: Process the Certificate

After receiving certificates from your CA:

### Build the Certificate Chain
```powershell
.\scripts\processing\Build-CertificateChain.ps1 -CertPath ".\certs\example.com.crt" -IntermediatePath ".\certs\intermediate.crt"
```

### Build the PFX Package
```powershell
.\scripts\processing\New-PfxPackage.ps1 -ChainPath ".\certs\chain.crt" -KeyPath ".\certs\example.com.key" -OutputPath ".\certs\example.com.pfx"
```

---

## Phase 4: Import to Key Vault

### Preview (dry-run, no changes)
```powershell
.\scripts\keyvault\Import-CertificateToKeyVault.ps1 -VaultName "your-keyvault" -CertName "your-cert" -PfxPath ".\certs\example.com.pfx" -Preview
```

### Execute (real import)
```powershell
.\scripts\keyvault\Import-CertificateToKeyVault.ps1 -VaultName "your-keyvault" -CertName "your-cert" -PfxPath ".\certs\example.com.pfx" -Execute
```

You will be prompted:
```
APPROVAL REQUIRED. Type CONFIRM to proceed:
```
Type `CONFIRM` exactly (case-sensitive) to approve the import.

### Python Import
```bash
python platform/main.py import --vault your-keyvault --cert your-cert --pfx ./certs/example.com.pfx --execute
```

---

## Phase 5: Validate the Import

```powershell
.\scripts\validation\Invoke-PostImportValidation.ps1 -VaultName "your-keyvault" -CertName "your-cert" -AppServiceName "your-app"
```

```bash
python platform/main.py validate --vault your-keyvault --cert your-cert --app your-app
```

This runs 7 validation checks and generates `reports/ValidationReport.md`.

---

## Phase 6: AI Risk Analysis

```bash
python platform/main.py ai-report
```

Generates:
- `reports/RiskReport.md` - certificates expiring in 30/60/90 days
- `reports/ExecutiveSummary.md` - management-level overview
- Jira updates for all at-risk certificates

---

## Phase 7: Generate Reports

```bash
python platform/main.py report
```

Generates HTML, CSV, JSON, and Markdown reports in the `reports/` directory.

---

## Phase 9: View the Dashboard

1. Run discovery to generate `reports/CertificateInventory.json`
2. Copy `CertificateInventory.json` to `dashboard/` directory
3. Open `dashboard/index.html` in a browser

The dashboard shows certificates expiring in 30/60/90 days, validation status, and Key Vault health.

---

## Phase 10: Jira Updates

```bash
python platform/main.py jira-update --event discovery-complete --ticket CERT-123
```

Available events: `discovery-complete`, `renewal-started`, `renewal-complete`,
`validation-complete`, `issue-detected`, `failure`, `risk-identified`

---

## Common Workflows

### Full Renewal Workflow
```bash
# 1. Discover
python platform/main.py discover

# 2. Review AI risk report
python platform/main.py ai-report

# 3. Generate CSR, process cert (PowerShell steps)
# 4. Preview import
# 5. Execute import with CONFIRM

# 6. Validate
python platform/main.py validate --vault your-kv --cert your-cert --app your-app

# 7. Generate final report
python platform/main.py report
```

---

## Getting Help

- Check `TROUBLESHOOTING.md` for common errors
- Check `QUICKSTART.md` for the 10-minute setup guide
- Check `OPERATIONS_GUIDE.md` for runbook procedures
- Run `python platform/main.py --help` for CLI reference
