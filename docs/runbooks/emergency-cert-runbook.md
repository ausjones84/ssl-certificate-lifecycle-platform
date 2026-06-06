# Emergency Certificate Replacement Runbook

**SSL Certificate Lifecycle Management Platform**

Use this runbook when a certificate has expired, is about to expire within 24 hours, or is presenting TLS errors.

---

## Severity

| Situation | Severity | Target Resolution |
|-----------|----------|-------------------|
| Certificate expired, site down | CRITICAL | < 2 hours |
| Certificate expires < 24 hours | HIGH | < 4 hours |
| TLS handshake errors | HIGH | < 2 hours |

---

## Step 1: Confirm the Problem

```bash
python platform/main.py discover
python platform/main.py ai-report
```

Check `reports/RiskReport.md`. Test the endpoint:
```powershell
.\scripts\validation\Test-CertificateEndpoint.ps1 -Hostname "affected-domain.com"
```

## Step 2: Notify and Create Jira Ticket

```bash
python platform/main.py jira-update --event issue-detected --ticket CERT-XXX
```

## Step 3: Generate Emergency CSR

```powershell
.\scripts\csr\New-CertificateRequest.ps1 -Domain "affected-domain.com" -SANs "www.affected-domain.com"
```

## Step 4: Submit to CA

1. Log into Sectigo Certificate Manager
2. Submit the .csr file
3. Complete DNS or HTTP validation
4. Download certificate and intermediate CA bundle

## Step 5: Build Chain and PFX

```powershell
.\scripts\processing\Build-CertificateChain.ps1 -CertPath ".\certs\affected.crt" -IntermediatePath ".\certs\intermediate.crt"
.\scripts\processing\New-PfxPackage.ps1 -ChainPath ".\certs\chain.crt" -KeyPath ".\certs\affected.key" -OutputPath ".\certs\affected.pfx"
```

## Step 6: Preview Import

```powershell
.\scripts\keyvault\Import-CertificateToKeyVault.ps1 -VaultName "your-kv" -CertName "your-cert" -PfxPath ".\certs\affected.pfx" -Preview
```

## Step 7: Execute Import

```powershell
.\scripts\keyvault\Import-CertificateToKeyVault.ps1 -VaultName "your-kv" -CertName "your-cert" -PfxPath ".\certs\affected.pfx" -Execute
```

Type `CONFIRM` at the prompt.

## Step 8: Validate

```powershell
.\scripts\validation\Invoke-PostImportValidation.ps1 -VaultName "your-kv" -CertName "your-cert" -AppServiceName "your-app"
```

All 7 checks must pass.

## Step 9: Close Out

```bash
python platform/main.py jira-update --event renewal-complete --ticket CERT-XXX
```

Attach ValidationReport.md to the Jira ticket and document root cause.
