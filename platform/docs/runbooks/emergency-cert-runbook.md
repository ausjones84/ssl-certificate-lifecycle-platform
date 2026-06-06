# Emergency Certificate Replacement Runbook

**SSL Certificate Lifecycle Management Platform**

Use this runbook when a certificate has expired, is about to expire within 24 hours, or is presenting TLS errors.

---

## Severity Assessment

| Situation | Severity | Target Resolution |
|-----------|----------|-------------------|
| Certificate expired, site down | CRITICAL | < 2 hours |
| Certificate expires < 24 hours | HIGH | < 4 hours |
| Certificate expires < 48 hours | MEDIUM | < 8 hours |
| TLS handshake errors reported | HIGH | < 2 hours |

---

## Step 1: Confirm the Problem

```bash
# Run discovery to confirm expiry
python platform/main.py discover
python platform/main.py ai-report
```

Check `reports/RiskReport.md` for expiry details.

Test the endpoint directly:
```powershell
.\scripts\validation\Test-CertificateEndpoint.ps1 -Hostname "affected-domain.com"
```

---

## Step 2: Notify Stakeholders

- Notify the engineering team immediately
- Create a Jira ticket:
```bash
python platform/main.py jira-update --event issue-detected --ticket CERT-XXX
```

---

## Step 3: Generate Emergency CSR

```powershell
.\scripts\csr\New-CertificateRequest.ps1 -Domain "affected-domain.com" -SANs "www.affected-domain.com"
```

Or using Python:
```bash
python platform/main.py csr --domain affected-domain.com --san "www.affected-domain.com"
```

---

## Step 4: Submit to CA (Sectigo)

1. Log into Sectigo Certificate Manager
2. Submit the `.csr` file
3. Choose Domain Control Validation (DCV)
4. Complete DNS or HTTP validation immediately
5. Request expedited issuance if available
6. Download: domain certificate (.crt) + intermediate CA bundle

---

## Step 5: Build Chain and PFX

```powershell
.\scripts\processing\Build-CertificateChain.ps1 -CertPath ".\certs\affected.crt" -IntermediatePath ".\certs\intermediate.crt"
.\scripts\processing\New-PfxPackage.ps1 -ChainPath ".\certs\chain.crt" -KeyPath ".\certs\affected.key" -OutputPath ".\certs\affected.pfx"
```

---

## Step 6: Preview Import

```powershell
.\scripts\keyvault\Import-CertificateToKeyVault.ps1 -VaultName "your-kv" -CertName "your-cert" -PfxPath ".\certs\affected.pfx" -Preview
```

Verify all values are correct before proceeding.

---

## Step 7: Execute Import (REQUIRES CONFIRM)

```powershell
.\scripts\keyvault\Import-CertificateToKeyVault.ps1 -VaultName "your-kv" -CertName "your-cert" -PfxPath ".\certs\affected.pfx" -Execute
```

Type `CONFIRM` at the prompt.

**This is the ONLY step that makes a production change.**

---

## Step 8: Validate Within 15 Minutes

```powershell
.\scripts\validation\Invoke-PostImportValidation.ps1 -VaultName "your-kv" -CertName "your-cert" -AppServiceName "your-app"
```

All 7 checks must pass. If any fail, see TROUBLESHOOTING.md.

---

## Step 9: Confirm HTTPS

```powershell
.\scripts\validation\Test-CertificateEndpoint.ps1 -Hostname "affected-domain.com"
```

Confirm the live certificate matches the new thumbprint.

---

## Step 10: Close Out

```bash
python platform/main.py jira-update --event renewal-complete --ticket CERT-XXX
```

- Update Jira ticket with resolution summary
- Attach ValidationReport.md
- Document root cause (expiry not caught, monitoring gap, etc.)
- Schedule post-incident review

---

## Escalation

If you cannot resolve within the target time:
1. Escalate to senior cloud engineer
2. Contact CA support for expedited issuance
3. Consider temporary workaround (HTTP redirect) if site must stay up
4. All actions must be documented in the Jira ticket
