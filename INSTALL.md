# INSTALL.md — Installation Guide

## Prerequisites

### Required Software

| Tool | Version | Installation |
|---|---|---|
| Python | 3.10+ | https://www.python.org/downloads/ |
| PowerShell | 7.x | https://aka.ms/powershell |
| Azure CLI | 2.50+ | https://aka.ms/installazurecliwindows |
| Az PowerShell Module | 10.x+ | `Install-Module -Name Az` |
| OpenSSL | 3.x | https://slproweb.com/products/Win32OpenSSL.html |
| Git | Latest | https://git-scm.com/ |

### Required Azure Permissions

| Permission | Where | Why |
|---|---|---|
| Key Vault Certificates Officer | Target Key Vault | Import/read certificates |
| Key Vault Secrets Officer | Target Key Vault | Read certificate secrets |
| Website Contributor | App Service | Read SSL bindings |
| Reader | Subscription | Discovery scan |

### Network Requirements

- Outbound access to `management.azure.com`
- Outbound access to `vault.azure.net`
- VPN/VDI access if Key Vault has private endpoint restrictions
- Sectigo API access (for CSR submission in Phase 2)

---

## Installation Steps

### Step 1: Clone the Repository

```bash
git clone https://github.com/ausjones84/ssl-certificate-lifecycle-platform.git
cd ssl-certificate-lifecycle-platform
```

### Step 2: Install Python Dependencies

```bash
pip install -r requirements.txt
```

Verify installation:
```bash
pip list | grep -E "azure|openpyxl|cryptography|requests"
```

### Step 3: Install PowerShell Dependencies

Open PowerShell 7 as Administrator:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
Install-Module -Name Az -AllowClobber -Repository PSGallery -Force
Install-Module -Name Az.Accounts -Repository PSGallery -Force
Install-Module -Name Az.KeyVault -Repository PSGallery -Force
Install-Module -Name Az.Websites -Repository PSGallery -Force
```

Verify:
```powershell
Get-Module -Name Az -ListAvailable
```

### Step 4: Install Azure CLI

```bash
# Windows (via winget)
winget install -e --id Microsoft.AzureCLI

# Verify
az --version
```

### Step 5: Install OpenSSL

```bash
# Windows — download from https://slproweb.com/products/Win32OpenSSL.html
# Add to PATH after installation

# Verify
openssl version
```

### Step 6: Configure the Platform

```bash
cp config/settings.json.example config/settings.json
cp config/certificate-inventory.json.example config/certificate-inventory.json
cp config/environments.json.example config/environments.json
```

Edit `config/settings.json`:
```json
{
  "subscription_id": "your-azure-subscription-id",
  "tenant_id": "your-azure-tenant-id",
  "key_vault_name": "tgna-kv-king-ctrl",
  "resource_group": "your-resource-group",
  "app_service_name": "interactive-king5",
  "sectigo_org_id": "your-sectigo-org-id",
  "notification_email": "your-email@company.com",
  "smtp_server": "smtp.company.com",
  "smtp_port": 587,
  "log_level": "INFO",
  "report_output_dir": "reports",
  "approval_required": true,
  "dry_run_default": true
}
```

**IMPORTANT:** Never commit `config/settings.json` — it is in `.gitignore`.

### Step 7: Authenticate with Azure

```bash
# Azure CLI (interactive browser)
az login

# Azure CLI (device code — recommended for VDI/RDP)
az login --use-device-code

# Verify login
az account show
az account list --output table

# Set correct subscription
az account set --subscription "your-subscription-name"
```

```powershell
# Az PowerShell (for PS scripts)
Connect-AzAccount
Select-AzSubscription -SubscriptionId "your-subscription-id"
```

### Step 8: Verify Installation

```bash
# Run the platform health check
python platform/main.py health-check
```

Expected output:
```
[PASS] Python 3.10+
[PASS] Azure CLI authenticated
[PASS] Az module available
[PASS] OpenSSL available
[PASS] Key Vault accessible: tgna-kv-king-ctrl
[PASS] Subscription: your-subscription-name
[PASS] Config file: config/settings.json
[PASS] Reports directory: reports/
All checks passed. Platform is ready.
```

---

## Configuration Reference

### settings.json Fields

| Field | Required | Description | Example |
|---|---|---|---|
| subscription_id | Yes | Azure subscription ID | "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" |
| tenant_id | Yes | Azure tenant ID | "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" |
| key_vault_name | Yes | Primary Key Vault name | "tgna-kv-king-ctrl" |
| resource_group | Yes | Resource group | "rg-king-production" |
| app_service_name | No | Primary App Service | "interactive-king5" |
| sectigo_org_id | No | Sectigo organization ID | "12345" |
| notification_email | No | Alert recipient | "ops-team@company.com" |
| smtp_server | No | SMTP server | "smtp.company.com" |
| smtp_port | No | SMTP port | 587 |
| log_level | No | Logging level | "INFO" or "DEBUG" |
| report_output_dir | No | Reports output directory | "reports" |
| approval_required | Yes | Require approval for imports | true |
| dry_run_default | Yes | Default dry-run mode | true |

### environments.json Structure

```json
{
  "environments": [
    {
      "name": "production",
      "subscription": "TGNA-PROD-C1",
      "resource_group": "rg-king-production",
      "key_vault": "tgna-kv-king-ctrl",
      "app_services": ["interactive-king5"],
      "certificates": ["king-wildcard"]
    }
  ]
}
```

---

## Firewall and Network Notes

If your Key Vault uses IP-based firewall rules, ensure:
1. Your current IP is in the allowed list, OR
2. You are connected to the VPN that is in the allowed list, OR  
3. You are running from a VDI that is in the allowed list

The platform will detect firewall blocks and provide clear error messages.

---

## Upgrading

```bash
git pull origin main
pip install -r requirements.txt --upgrade
```

---

## Uninstalling

```bash
cd ..
rm -rf ssl-certificate-lifecycle-platform
```

The platform does not modify any system files. All output is written to the `reports/` directory within the repository.

---

See [QUICKSTART.md](QUICKSTART.md) to be operational in under 10 minutes after installation.
