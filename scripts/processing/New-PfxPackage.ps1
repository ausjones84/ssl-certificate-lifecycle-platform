<#
.SYNOPSIS
    Generate a PFX (PKCS#12) package from a certificate chain and private key.
.DESCRIPTION
    Phase 3 - Certificate Processing.
    Combines a certificate chain file with a private key to produce a PFX
    package suitable for import into Azure Key Vault.
.PARAMETER ChainPath
    Path to the full certificate chain file (.crt or .pem).
.PARAMETER KeyPath
    Path to the private key file (.key). Never logged or displayed.
.PARAMETER OutputPath
    Output path for the PFX file. Defaults to certificate.pfx.
.PARAMETER PfxPassword
    Optional PFX password. Leave empty for passwordless PFX.
.EXAMPLE
    .\New-PfxPackage.ps1 -ChainPath .\chain.crt -KeyPath .\example.com.key -OutputPath .\example.com.pfx
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]  [string]$ChainPath,
    [Parameter(Mandatory=$true)]  [string]$KeyPath,
    [Parameter(Mandatory=$false)] [string]$OutputPath = "",
    [Parameter(Mandatory=$false)] [string]$PfxPassword = ""
)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
function Write-Status {
    param([string]$Msg, [string]$Lvl = "INFO")
    $c = switch($Lvl){"SUCCESS"{"Green"}"WARN"{"Yellow"}"ERROR"{"Red"}default{"Cyan"}}
    Write-Host "[$((Get-Date -Format "HH:mm:ss"))] [$Lvl] $Msg" -ForegroundColor $c
}
if ($null -eq (Get-Command openssl -EA SilentlyContinue)) {
    Write-Status "OpenSSL not found in PATH. Install from https://slproweb.com/products/Win32OpenSSL.html" "ERROR"
    exit 1
}
if (-not (Test-Path $ChainPath)) { Write-Status "Chain file not found: $ChainPath" "ERROR"; exit 1 }
if (-not (Test-Path $KeyPath))   { Write-Status "Key file not found: $KeyPath" "ERROR"; exit 1 }
if ([string]::IsNullOrEmpty($OutputPath)) {
    $OutputPath = Join-Path (Split-Path -Parent (Resolve-Path $ChainPath)) "certificate.pfx"
}
Write-Status "Generating PFX package" "INFO"
Write-Status "  Chain  : $ChainPath" "INFO"
Write-Status "  Key    : [PRIVATE KEY - NOT DISPLAYED]" "INFO"
Write-Status "  Output : $OutputPath" "INFO"
if ([string]::IsNullOrEmpty($PfxPassword)) {
    Write-Status "No PFX password - Azure Key Vault accepts passwordless PFX" "WARN"
    $r = & openssl pkcs12 -export -out $OutputPath -inkey $KeyPath -in $ChainPath -passout pass: 2>&1
} else {
    $r = & openssl pkcs12 -export -out $OutputPath -inkey $KeyPath -in $ChainPath -passout "pass:$PfxPassword" 2>&1
}
if ($LASTEXITCODE -ne 0) { Write-Status "PFX generation failed: $r" "ERROR"; exit 1 }
if (-not (Test-Path $OutputPath)) { Write-Status "PFX file not created." "ERROR"; exit 1 }
Write-Status "PFX generated: $OutputPath ($((Get-Item $OutputPath).Length) bytes)" "SUCCESS"
Write-Status "Validating PFX..." "INFO"
if ([string]::IsNullOrEmpty($PfxPassword)) {
    $v = & openssl pkcs12 -in $OutputPath -noout -passin pass: 2>&1
} else {
    $v = & openssl pkcs12 -in $OutputPath -noout -passin "pass:$PfxPassword" 2>&1
}
if ($LASTEXITCODE -eq 0) { Write-Status "PFX validation PASSED" "SUCCESS" }
else { Write-Status "PFX validation warning: $v" "WARN" }
Write-Status "PFX ready. Next: Import-CertificateToKeyVault.ps1 -Preview" "SUCCESS"
