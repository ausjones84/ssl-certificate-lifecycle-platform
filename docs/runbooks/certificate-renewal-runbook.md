# Certificate Renewal Runbook

## Scope
Standard certificate renewal for TGNA/King5 Azure App Services.

## Pre-Renewal Checklist
- Identify expiring cert from: python platform/main.py ai-report --days 30
- Confirm Key Vault name and certificate name
- Verify Azure auth: az account show
- Verify Key Vault firewall access

## Step 1: Discovery and Jira
    python platform/main.py discover
    python platform/main.py ai-report --days 30
    python platform/main.py jira-update --cert king-wildcard --stage renewal-started

## Step 2: Generate CSR
    .\scripts\csr\New-CertificateRequest.ps1 -CommonName "*.king5.com" -OutputPath "C:\certs"

INPUT: .*.king5.com.csr to Sectigo | KEY FILE IS PRIVATE - NEVER SHARE

## Step 3: Submit to Sectigo (Manual)
1. Log in to Sectigo Certificate Manager
2. Enroll new SSL certificate, paste CSR
3. Complete domain validation
4. Wait for issuance (1-24 hours)
5. Download certificate files

## Step 4: Build Chain and PFX
    .\scripts\processing\Build-CertificateChain.ps1 -CertPath king5.cer -IntermediatePath sectigo-int.cer
    .\scripts\processing\New-PfxPackage.ps1 -CertPath king5-fullchain.pem -KeyPath king5.key

## Step 5: Import to Key Vault
    # Preview (no changes)
    python platform/main.py import --cert king-wildcard --pfx king5.pfx --preview
    # Dry run (simulate)
    python platform/main.py import --cert king-wildcard --pfx king5.pfx --dry-run
    # Execute (type CONFIRM when prompted)
    python platform/main.py import --cert king-wildcard --pfx king5.pfx --execute

## Step 6: Validate and Close
    python platform/main.py validate --cert king-wildcard --hostname king5.com
    python platform/main.py jira-update --cert king-wildcard --stage renewal-complete

- Attach ValidationReport.md to Jira ticket
- Verify HTTPS in browser (confirm new expiry date)
- Securely delete private key from local machine

## Timing Reference
| Step | Time |
|---|---|
| CSR + submission | 10 min |
| Certificate issuance | 1-24 hours |
| Chain + PFX | 5 min |
| Import + validation | 15 min |

*Runbook v1.0 | SSL Certificate Lifecycle Platform*
