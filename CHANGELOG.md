# CHANGELOG.md

All notable changes to the SSL Certificate Lifecycle Platform are documented in this file.

Format: [Version] - Date — Changes

---

## [1.0.0] - 2026-06-05

### Initial Release

**Platform Foundation**
- Complete Python orchestration engine (platform/)
- Azure CLI wrapper with 3-attempt exponential backoff retry
- Structured dual-output logging (console + file)
- Platform-wide configuration system (config/settings.json)

**Phase 1 — Certificate Discovery**
- Automated Azure Key Vault scanning
- Automated App Service SSL binding discovery
- Certificate-to-App-Service mapping
- Risk level calculation (EXPIRED/CRITICAL/HIGH/MEDIUM/LOW/OK)
- Multi-format inventory output (CSV/JSON/MD)
- PowerShell discovery script (Invoke-CertificateDiscovery.ps1)

**Phase 2 — CSR Automation**
- OpenSSL-based CSR generation (New-CertificateRequest.ps1)
- CN and SAN validation
- Config file generation
- CSR artifact management

**Phase 3 — Certificate Processing**
- Certificate chain building
- PFX packaging
- PFX validation

**Phase 4 — Key Vault Import with Approval Gate**
- 3-layer approval gate (flag + config + interactive CONFIRM)
- Preview Mode (show proposal, no Azure calls)
- Dry-Run Mode (simulate import, no Azure writes)
- Execute Mode (full import after approval)
- Python orchestrator (platform/keyvault_ops.py)
- PowerShell script (Import-CertificateToKeyVault.ps1)

**Phase 5 — Post-Import Validation**
- 7-point validation suite
- Key Vault certificate existence check
- Certificate enabled check
- Expiration check
- Key Vault status check
- App Service SSL binding check
- HTTPS endpoint check
- Live certificate thumbprint check
- ValidationReport.md generation
- Python validator (platform/validator.py)
- PowerShell script (Invoke-PostImportValidation.ps1)

**Phase 6 — AI Operations Layer**
- Certificate inventory analysis
- Risk classification and narrative generation
- 30/60/90-day expiry alerts
- Executive summary generation
- Engineer summary generation
- Optional OpenAI GPT integration for enhanced narratives
- Risk report generation (RiskReport.md)

**Phase 7 — Multi-Format Reporting**
- Markdown reports
- HTML reports with colour-coded styling
- CSV reports
- JSON reports
- Operations report generation

**Phase 8 — Documentation Suite**
- README.md — Platform overview
- INSTALL.md — Installation guide
- QUICKSTART.md — 10-minute onboarding
- USER_GUIDE.md — Complete user guide
- ARCHITECTURE.md — Technical architecture
- OPERATIONS_GUIDE.md — Day-to-day operations
- TROUBLESHOOTING.md — Issue resolution guide
- CHANGELOG.md — This file

**Phase 9 — Dashboard**
- HTML/CSS/JS certificate lifecycle dashboard
- No server required — open in browser
- Real-time inventory loading from reports/CertificateInventory.json
- Demo data fallback for testing
- Expiry risk cards (30/60/90 days)
- Searchable and filterable certificate table
- Action Required section for critical/expiring certs

**Phase 10 — Jira Automation**
- Ready-to-paste Jira update templates
- 7 lifecycle stages: discovery-complete, renewal-started, renewal-complete, validation-complete, issue-detected, failure, risk-identified
- Jira wiki markup format
- Structured detail substitution

**Azure DevOps Pipeline**
- 5-stage pipeline (Discovery → Preview → Approval Gate → Import → Validation)
- ManualValidation@0 approval gate (24-hour window)
- AzurePowerShell@5 task integration
- Parameterized environments (production/staging)
- Artifact publishing for reports

**Security**
- No secrets in repository
- .gitignore excludes all certificate artifacts and config files
- Approval gate on all production Key Vault writes
- Dry-run default to prevent accidental changes
- Sensitive value masking in all log output

---

## Upcoming (Planned)

### [1.1.0]
- Sectigo API integration for automated CSR submission
- Scheduled discovery via GitHub Actions cron
- Excel (XLSX) report format
- Email digest for weekly certificate status
- Certificate renewal SLA tracking

### [1.2.0]
- Certificate expiry webhook notifications (Teams/Slack)
- Multi-vault batch operations
- Certificate comparison (before/after import)
- Automated App Service synchronization trigger

---

*SSL Certificate Lifecycle Platform | Self-contained | Zero tribal knowledge required*
