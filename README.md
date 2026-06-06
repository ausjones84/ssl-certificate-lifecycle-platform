# SSL Certificate Lifecycle Management Platform

> **Enterprise-grade, self-contained SSL certificate lifecycle automation for Azure.**

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](CHANGELOG.md) [![Python](https://img.shields.io/badge/Python-3.10+-green.svg)](https://www.python.org/) [![PowerShell](https://img.shields.io/badge/PowerShell-7.x-blue.svg)](https://docs.microsoft.com/powershell/) [![Azure](https://img.shields.io/badge/Azure-Key%20Vault-0089D6.svg)](https://azure.microsoft.com/)

---

## Purpose

Replaces a fully manual SSL certificate lifecycle process with enterprise-grade automation. Every phase is handled by this single, self-contained repository.

**Zero external repository dependencies. Clone it, configure it, run it. Zero tribal knowledge required.**

---

## Business Process Replaced

| Manual Step | Automated By |
|---|---|
| Generate CSR | scripts/csr/New-CertificateRequest.ps1 |
| Submit to Sectigo | platform/csr_generator.py |
| Build certificate chain | scripts/processing/Build-CertificateChain.ps1 |
| Generate PFX | scripts/processing/New-PfxPackage.ps1 |
| Import into Key Vault | scripts/keyvault/Import-CertificateToKeyVault.ps1 |
| Validate App Service | scripts/validation/Test-AppServiceBinding.ps1 |
| Validate HTTPS | scripts/validation/Test-CertificateEndpoint.ps1 |
| Update Jira | platform/jira_templates.py |

---

## Quick Start

See QUICKSTART.md to be operational in under 10 minutes.

    git clone https://github.com/ausjones84/ssl-certificate-lifecycle-platform.git
    cd ssl-certificate-lifecycle-platform
    pip install -r requirements.txt
    cp config/settings.json.example config/settings.json
    az login --use-device-code
    python platform/main.py discover --subscription "TGNA-PROD-C1"
    python platform/main.py ai-report --days 90
    python platform/main.py import --cert king-wildcard --preview

---

## Platform Phases

**Phase 1: Discovery** - Automated Azure scanning. Outputs CertificateInventory.csv/.json/.md.

**Phase 2: CSR Automation** - Generate and validate CSRs with correct CN/SAN.

**Phase 3: Certificate Processing** - Build chains, package PFX, validate integrity.

**Phase 4: Key Vault Import (3-Layer Approval Gate)**
- Layer 1: `--execute` flag required
- Layer 2: `approval_required: true` in config
- Layer 3: Interactive `CONFIRM` typed at runtime

    PROPOSED IMPORT
    Vault      : tgna-kv-king-ctrl
    Certificate: king-wildcard
    Expiration : 2027-06-09
    Type CONFIRM to proceed: _

**Phase 5: Post-Import Validation (7-point check)**
1. Certificate exists in Key Vault
2. Certificate enabled  3. Not expired
4. Key Vault status OK  5. App Service binding present
6. HTTPS endpoint reachable  7. Live cert thumbprint matches

**Phase 6: AI Operations** - Risk analysis, expiry alerts (30/60/90 days), human-readable narratives.

Example: "Certificate king-wildcard expires in 14 days. App Service interactive-king5 is consuming this from Key Vault tgna-kv-king-ctrl. Immediate renewal required. Risk: CRITICAL."

**Phase 7: Reporting** - MD, HTML, CSV, JSON reports.

**Phase 8: Documentation** - Complete docs suite (INSTALL, QUICKSTART, USER_GUIDE, ARCHITECTURE, OPERATIONS_GUIDE, TROUBLESHOOTING, CHANGELOG).

**Phase 9: Dashboard** - Open `dashboard/index.html` in any browser. No server needed.

**Phase 10: Jira Automation** - Ready-to-paste Jira updates for every lifecycle stage.

---

## Current Certificate Mapping

| App Service | Certificate | Key Vault | Secret | Expires |
|---|---|---|---|---|
| interactive-king5 | tgna-kv-king-ctrl-king-wildcard | tgna-kv-king-ctrl | king-wildcard | 06/09/2026 |

---

## Security Controls

- No secrets stored in repository. config/settings.json is gitignored.
- Certificate artifacts (.pfx .key .crt) are gitignored
- No production changes without explicit typed CONFIRM
- Dry-run mode for all write operations
- Full audit trail in structured timestamped log files

---

## Documentation

| Document | Purpose |
|---|---|
| INSTALL.md | Prerequisites and installation |
| QUICKSTART.md | Operational in 10 minutes |
| USER_GUIDE.md | Complete operational guide |
| ARCHITECTURE.md | Technical architecture |
| OPERATIONS_GUIDE.md | Day-to-day operations |
| TROUBLESHOOTING.md | Issue resolution |
| CHANGELOG.md | Version history |

---

*Self-contained. Zero external dependencies. Built for TGNA/King5 Azure infrastructure.*
