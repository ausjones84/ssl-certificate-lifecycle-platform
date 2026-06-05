<#
.SYNOPSIS
    Phase 5: Post-Import Validation - 7-point certificate validation suite.

.DESCRIPTION
    Validates a certificate after Key Vault import across 7 checks:
    1. Certificate exists in Key Vault
    2. Certificate is enabled
    3. Certificate not expired
    4. Key Vault status OK
    5. App Service SSL binding present
    6. HTTPS endpoint reachable
    7. Live certificate thumbprint matches
    Generates reports/ValidationReport.md

.EXAMPLE
    .\Invoke-PostImportValidation.ps1 -VaultName "tgna-kv-king-ctrl" -CertName "king-wildcard" -AppServiceName "interactive-king5" -Hostname "king5.com"
#>

[CmdletBinding()]
param (
    [Parameter(Mandatory = $true)][string]$VaultName,
    [Parameter(Mandatory = $true)][string]$CertName,
    [Parameter(Mandatory = $false)][string]$AppServiceName = "",
    [Parameter(Mandatory = $false)][string]$ResourceGroupName = "",
    [Parameter(Mandatory = $false)][string]$Hostname = "",
    [Parameter(Mandatory = $false)][string]$ExpectedThumbprint = "",
    [Parameter(Mandatory = $false)][string]$OutputDir = "reports"
)

$ErrorActionPreference = "Stop"
$StartTime = Get-Date
$Results = @()
$PassCount = 0
$FailCount = 0

function Add-Check {
    param([string]$Name, [bool]$Passed, [string]$Detail = "")
    $script:Results += [PSCustomObject]@{ Check = $Name; Status = if ($Passed) {"PASS"} else {"FAIL"}; Detail = $Detail }
    if ($Passed) {
        Write-Host "  [PASS] $Name $Detail" -ForegroundColor Green
        $script:PassCount++
    } else {
        Write-Host "  [FAIL] $Name $Detail" -ForegroundColor Red
        $script:FailCount++
    }
}

Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host " POST-IMPORT VALIDATION" -ForegroundColor Cyan
Write-Host " Vault: $VaultName | Certificate: $CertName" -ForegroundColor Cyan
Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host ""

# Check 1: Certificate exists
Write-Host "[1/7] Certificate Exists in Key Vault" -ForegroundColor White
try {
    $KvCert = Get-AzKeyVaultCertificate -VaultName $VaultName -Name $CertName
    Add-Check "Certificate exists in Key Vault" ($null -ne $KvCert) "Version: $($KvCert.Version)"
} catch {
    Add-Check "Certificate exists in Key Vault" $false "Error: $_"
}

# Check 2: Certificate enabled
Write-Host ""
Write-Host "[2/7] Certificate Enabled" -ForegroundColor White
if ($KvCert) {
    Add-Check "Certificate is enabled" ($KvCert.Enabled -eq $true) "Enabled: $($KvCert.Enabled)"
} else { Add-Check "Certificate is enabled" $false "Certificate not found" }

# Check 3: Not expired
Write-Host ""
Write-Host "[3/7] Expiration Check" -ForegroundColor White
if ($KvCert -and $KvCert.Expires) {
    $Days = [int]($KvCert.Expires - (Get-Date)).TotalDays
    Add-Check "Certificate not expired" ($Days -gt 0) "Expires: $($KvCert.Expires.ToString("yyyy-MM-dd")) ($Days days)"
    if ($ExpectedThumbprint -ne "" -and $KvCert.Thumbprint) {
        Add-Check "Thumbprint matches expected" ($KvCert.Thumbprint -like "$($ExpectedThumbprint.Substring(0,[Math]::Min(8,$ExpectedThumbprint.Length)))*") "KV: $($KvCert.Thumbprint.Substring(0,16))"
    }
} else { Add-Check "Certificate not expired" $false "No expiry date found" }

# Check 4: Key Vault status
Write-Host ""
Write-Host "[4/7] Key Vault Status" -ForegroundColor White
try {
    $Kv = Get-AzKeyVault -VaultName $VaultName
    Add-Check "Key Vault provisioned" ($Kv.ProvisioningState -eq "Succeeded") "State: $($Kv.ProvisioningState)"
} catch { Add-Check "Key Vault status" $false "Cannot query Key Vault" }

# Check 5: App Service binding
Write-Host ""
Write-Host "[5/7] App Service Binding" -ForegroundColor White
if ($AppServiceName -ne "") {
    try {
        $AppConfig = if ($ResourceGroupName) {
            Get-AzWebApp -ResourceGroupName $ResourceGroupName -Name $AppServiceName
        } else { Get-AzWebApp -Name $AppServiceName }
        $Bindings = $AppConfig.HostNameSslStates | Where-Object { $_.SslState -ne "Disabled" }
        Add-Check "App Service SSL binding present" ($Bindings.Count -gt 0) "$($Bindings.Count) binding(s)"
    } catch { Add-Check "App Service SSL binding" $false "Cannot query App Service $AppServiceName" }
} else { Write-Host "  [SKIP] App Service name not provided" -ForegroundColor Gray }

# Check 6: HTTPS endpoint
Write-Host ""
Write-Host "[6/7] HTTPS Endpoint" -ForegroundColor White
if ($Hostname -ne "") {
    try {
        $Response = Invoke-WebRequest -Uri "https://$Hostname" -UseBasicParsing -TimeoutSec 15 -ErrorAction Stop
        Add-Check "HTTPS endpoint reachable" ($Response.StatusCode -lt 500) "HTTP $($Response.StatusCode)"
    } catch { Add-Check "HTTPS endpoint reachable" $false "Error: $_" }
} else { Write-Host "  [SKIP] Hostname not provided" -ForegroundColor Gray }

# Check 7: Live certificate
Write-Host ""
Write-Host "[7/7] Live Certificate" -ForegroundColor White
if ($Hostname -ne "") {
    try {
        $Tcp = [System.Net.Sockets.TcpClient]::new($Hostname, 443)
        $Ssl = [System.Net.Security.SslStream]::new($Tcp.GetStream(), $false, { $true })
        $Ssl.AuthenticateAsClient($Hostname)
        $LiveCert = $Ssl.RemoteCertificate
        $LiveThumb = [System.Security.Cryptography.X509Certificates.X509Certificate2]::new($LiveCert.Export([System.Security.Cryptography.X509Certificates.X509ContentType]::Cert)).Thumbprint
        Add-Check "Live certificate presented" $true "Live thumbprint: $($LiveThumb.Substring(0,16))..."
        if ($KvCert -and $KvCert.Thumbprint) {
            Add-Check "Live thumbprint matches KV" ($LiveThumb -eq $KvCert.Thumbprint) "Live: $($LiveThumb.Substring(0,8)) KV: $($KvCert.Thumbprint.Substring(0,8))"
        }
        $Ssl.Dispose(); $Tcp.Dispose()
    } catch { Add-Check "Live certificate check" $false "Error: $_" }
} else { Write-Host "  [SKIP] Hostname not provided" -ForegroundColor Gray }

# Summary
$Duration = [int]((Get-Date) - $StartTime).TotalSeconds
Write-Host ""
Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host " VALIDATION SUMMARY" -ForegroundColor Cyan
Write-Host (" Passed : $PassCount") -ForegroundColor Green
Write-Host (" Failed : $FailCount") -ForegroundColor $(if ($FailCount -gt 0) {"Red"} else {"Green"})
Write-Host (" Duration: ${Duration}s") -ForegroundColor Cyan
Write-Host ("=" * 70) -ForegroundColor Cyan

# Write Markdown report
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
$RunDate = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$Status = if ($FailCount -gt 0) {"FAILED"} else {"PASSED"}
$Md = "# Post-Import Validation Report`n`n**Generated:** $RunDate  `n**Vault:** $VaultName | **Certificate:** $CertName  `n**Status:** $Status ($PassCount/$($PassCount+$FailCount) passed)  `n`n| Check | Result | Detail |`n|---|---|---|`n"
foreach ($R in $Results) { $Md += "| $($R.Check) | $($R.Status) | $($R.Detail) |`n" }
Set-Content -Path (Join-Path $OutputDir "ValidationReport.md") -Value $Md -Encoding UTF8
Write-Host ""
Write-Host "Validation report: $OutputDir\ValidationReport.md" -ForegroundColor Gray
if ($FailCount -gt 0) { exit 1 } else { exit 0 }
