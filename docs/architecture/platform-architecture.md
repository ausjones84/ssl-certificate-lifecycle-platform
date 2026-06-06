# Platform Architecture

The SSL Certificate Lifecycle Platform is a self-contained, multi-layer automation platform for enterprise Azure SSL certificate operations.

## Design Principles

- **Self-contained** — no external repository dependencies
- **Approval-gated** — no production changes without explicit confirmation
- **Dry-run first** — all write operations support dry-run simulation
- **Audit trail** — every operation logged to timestamped files
- **Multi-format output** — all reports generated in CSV, JSON, MD, HTML
- **Zero tribal knowledge** — complete documentation for any engineer

## Layer Architecture

```
CLI Layer (platform/main.py)
|
Orchestration Layer
|- discovery.py      Phase 1: Azure scanning
|- inventory.py      Phase 1: Multi-format output
|- csr_generator.py  Phase 2: CSR generation
|- keyvault_ops.py   Phase 4: KV import + approval gate
|- validator.py      Phase 5: Post-import validation
|- ai_layer.py       Phase 6: Risk analysis + AI
|- reporting.py      Phase 7: Report generation
|- jira_templates.py Phase 10: Jira updates
|
Infrastructure Layer
|- azure_client.py   Azure CLI wrapper + retry
|- logger.py         Structured dual-output logging
|- notifications.py  Email notifications
|
Azure Services
|- Azure Key Vault
|- Azure App Services
|- Azure CLI (authenticated)
```

## Component Details

### platform/azure_client.py
Wraps all Azure CLI calls with 3-attempt exponential backoff (2s/4s/8s). Validates authentication on startup. Handles subscription context switching.

### platform/logger.py
Dual-output: INFO+ to console (coloured), DEBUG+ to file. Log files: `logs/CERT_LIFECYCLE_YYYYMMDD_HHMMSS.log`. Uses rich library for console formatting if available.

### platform/keyvault_ops.py (Approval Gate)
Three safety layers, all required:
- Layer 1: `mode='execute'` must be passed explicitly
- Layer 2: `approval_required=true` in `config/settings.json`
- Layer 3: Interactive `CONFIRM` typed at runtime

No import occurs unless all three pass.

### platform/validator.py (7-Point Validation)
1. Certificate exists in Key Vault
2. Certificate is enabled
3. Certificate not expired
4. Key Vault provisioning state = Succeeded
5. App Service SSL binding present
6. HTTPS endpoint returns HTTP < 500
7. Live certificate thumbprint presented

### platform/ai_layer.py
Rule-based risk analysis with optional OpenAI GPT-4o-mini enhancement. Classifies certificates by risk tier, generates human-readable narratives, builds risk reports and executive summaries.

## Data Flow

```
Discovery
-> CertificateRecord objects (in memory)
-> InventoryBuilder
-> reports/CertificateInventory.{csv,json,md}

Key Vault Import
-> Pre-flight validation
-> Preview / Dry-Run / Execute mode
-> 3-layer approval gate (execute only)
-> import_keyvault_certificate()
-> Post-import validation
-> reports/ValidationReport.md

AI Analysis
-> Load inventory JSON
-> AIOperationsLayer.analyze_inventory()
-> reports/RiskReport.md
-> reports/ExecutiveSummary.md
```

## Security Architecture

- `config/settings.json` is gitignored (never committed)
- Certificate artifacts (.pfx, .key, .crt) are gitignored
- Private keys never appear in logs (masked)
- Production operations require interactive CONFIRM
- All Azure calls use least-privilege RBAC
- Dry-run default prevents accidental writes

## Technology Stack

| Layer | Technology |
|-------|------------|
| Orchestration | Python 3.10+ |
| Azure Operations | Azure CLI + Az PowerShell |
| Certificate Operations | OpenSSL + cryptography |
| Reporting | openpyxl, pandas, Jinja2 |
| Logging | Python logging + rich |
| AI Layer | openai (optional) |
| CI/CD | Azure DevOps + GitHub Actions |
| Dashboard | HTML/CSS/JS (no framework) |
