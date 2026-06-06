# Certificate Renewal Runbook

## Overview

This runbook covers the end-to-end certificate renewal process for Azure-hosted App Services using Key Vault.

## Applicability

Use this runbook for any certificate renewal for TGNA/King5 Azure App Services.

---

## Pre-Renewal Checklist

- [ ] Identify expiring certificate (from ai-report or discovery)
- [ ] Confirm Key Vault name and certificate name
- [ ] Confirm App Service name
- [ ] Verify Azure authentication (az account show)
- [ ] Verify Key Vault firewall access from current IP
- [ ] Sectigo account accessible
- [ ] Raise change request if required by CAB

---

## Step 1: Discovery

    python platform/main.py discover
    python platform/main.py ai-report --days 30

Identify certificate to renew from output.

## Step 2: Generate Jira Update

    python platform/main.py jira-update --cert king-wildcard --stage renewal-started

Copy output to Jira ticket.

## Step 3: Generate CSR

    .\scripts\csr\New-CertificateRequest.ps1 -CommonName "*.king5.com" -OutputPath "C:\certs"

Outputs:
- C:\certs\*.king5.com\*.king5.com.csr (submit this to Sectigo)
- C:\certs\*.king5.com\*.king5.com.key (PRIVATE KEY - do not share)

## Step 4: Submit to Sectigo

1. Log in to Sectigo Certificate Manager
2. Navigate to SSL Certificates > Enroll
3. Paste CSR content
4. Select appropriate certificate type (wildcard/OV/DV)
5. Complete domain validation as prompted
6. Wait for issuance (typically 1-24 hours)

## Step 5: Download Certificate

From Sectigo portal:
1. Download certificate file (.cer or .crt)
2. Download intermediate chain if not bundled
3. Save to same directory as CSR

## Step 6: Build Chain and PFX

    .\scripts\processing\Build-CertificateChain.ps1 -CertPath "C:\certs\*.king5.com\*.king5.com.cer" -ChainPath "C:\certs\sectigo-intermediate.cer"
    .\scripts\processing\New-PfxPackage.ps1 -CertPath "C:\certs\*.king5.com\full-chain.cer" -KeyPath "C:\certs\*.king5.com\*.king5.com.key"

## Step 7: Import Preview

    python platform/main.py import --cert king-wildcard --vault tgna-kv-king-ctrl --pfx "C:\certs\*.king5.com\king5.pfx" --preview

Review output. Confirm vault, cert name, and PFX details are correct.

## Step 8: Dry Run

    python platform/main.py import --cert king-wildcard --vault tgna-kv-king-ctrl --pfx "C:\certs\*.king5.com\king5.pfx" --dry-run

Confirm dry run shows no errors.

## Step 9: Execute Import (Approval Required)

    python platform/main.py import --cert king-wildcard --vault tgna-kv-king-ctrl --pfx "C:\certs\*.king5.com\king5.pfx" --execute

Type CONFIRM when prompted.

## Step 10: Post-Import Validation

    python platform/main.py validate --cert king-wildcard --hostname king5.com

All 7 checks must pass. Review reports/ValidationReport.md.

## Step 11: Verify App Service

Wait 5-10 minutes, then verify HTTPS in browser:
- https://king5.com
- Check certificate in browser padlock icon
- Confirm new expiry date

## Step 12: Close Out

    python platform/main.py jira-update --cert king-wildcard --stage renewal-complete

- Attach ValidationReport.md to Jira ticket
- Update change request with completion status
- Store PFX securely (password-protected)
- Securely delete private key from local machine

---

## Timing Reference

| Step | Estimated Time |
|---|---|
| CSR generation | 2 minutes |
| Sectigo submission | 5 minutes |
| Domain validation | 5-30 minutes |
| Certificate issuance | 1-24 hours |
| Chain build + PFX | 5 minutes |
| Import + validation | 10 minutes |
| Total (excl issuance) | ~30 minutes |

---

## Contacts

- Sectigo Support: support.sectigo.com
- Azure Operations: [update with team contact]
- Platform Owner: [update with owner]

---

*Runbook version 1.0 | SSL Certificate Lifecycle Platform*
