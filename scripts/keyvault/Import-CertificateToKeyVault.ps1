<#
.SYNOPSIS
    Phase 4: Import a certificate into Azure Key Vault with approval gate.

.DESCRIPTION
    Imports a PFX certificate into Azure Key Vault.
    REQUIRES explicit approval before any write operation.
    Supports -Preview, -DryRun, and -Execute modes.

.PARAMETER VaultName
    Target Key Vault name (e.g., tgna-kv-king-ctrl)
.PARAMETER CertName
    Certificate name in Key Vault (e.g., king-wildcard)
.PARAMETER PfxPath
    Full path to the PFX file
.PARAMETER PfxPassword
    PFX password as SecureString (leave empty if none)
.PARAMETER Preview
    Show what would happen. No changes made.
.PARAMETER DryRun
    Simulate the full import. No changes made.
.PARAMETER Execute
    Execute the import after approval confirmation.

.EXAMPLE
    .\Import-CertificateToKeyVault.ps1 -VaultName "tgna-kv-king-ctrl" -CertName "king-wildcard" -PfxPath "C:\certs\king5.pfx" -Preview
.EXAMPLE
    .\Import-CertificateToKeyVault.ps1 -VaultName "tgna-kv-king-ctrl" -CertName "king-wildcard" -PfxPath "C:\certs\king5.pfx" -Execute
#>

[CmdletBinding()]
param (
    [Parameter(Mandatory = $true)][string]$VaultName,
    [Parameter(Mandatory = $true)][string]$CertName,
    [Parameter(Mandatory = $true)][string]$PfxPath,
    [Parameter(Mandatory = $false)][SecureString]$PfxPassword = $null,
    [switch]$Preview,
    [switch]$DryRun,
    [switch]$Execute
)

$ErrorActionPreference = "Stop"
$StartTime = Get-Date

function Add-Result {
    param([string]$Check, [bool]$Passed, [string]$Detail = "")
    if ($Passed) { Write-Host "  [PASS] $Check $Detail" -ForegroundColor Green }
    else { Write-Host "  [FAIL] $Check $Detail" -ForegroundColor Red }
}

Write-Host ""
Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host " SSL Certificate Lifecycle Platform - Key Vault Import" -ForegroundColor Cyan
Write-Host " Vault      : $VaultName" -ForegroundColor Cyan
Write-Host " Certificate: $CertName" -ForegroundColor Cyan
Write-Host " PFX Path   : $PfxPath" -ForegroundColor Cyan
$ModeLabel = if ($Execute) { "EXECUTE" } elseif ($DryRun) { "DRY-RUN" } else { "PREVIEW" }
Write-Host " Mode       : $ModeLabel" -ForegroundColor Cyan
Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host ""

# Pre-flight validation
Write-Host "Pre-flight Validation" -ForegroundColor White

# Check PFX exists
if (-not (Test-Path $PfxPath)) {
    Write-Error "PFX file not found: $PfxPath"
    exit 1
}
Add-Result "PFX file exists" $true "($((Get-Item $PfxPath).Length) bytes)"

# Check PFX is valid
try {
    if ($PfxPassword) {
        $Cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($PfxPath, $PfxPassword)
    } else {
        $Cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($PfxPath)
    }
    $ExpDays = [int]($Cert.NotAfter - (Get-Date)).TotalDays
    Add-Result "PFX is valid" $true "Subject: $($Cert.Subject)"
    Add-Result "Certificate not expired" ($ExpDays -gt 0) "Expires: $($Cert.NotAfter.ToString("yyyy-MM-dd")) ($ExpDays days)"
    Add-Result "Thumbprint readable" ($Cert.Thumbprint -ne "") "Thumbprint: $($Cert.Thumbprint.Substring(0,16))..."
    $Thumbprint = $Cert.Thumbprint
    $ExpiryDate = $Cert.NotAfter.ToString("yyyy-MM-dd")
} catch {
    Add-Result "PFX is valid" $false "Error: $_"
    if (-not $Preview) { exit 1 }
}

# Check Key Vault accessibility
try {
    $KvCheck = Get-AzKeyVault -VaultName $VaultName -ErrorAction Stop
    Add-Result "Key Vault accessible" $true "Location: $($KvCheck.Location)"
} catch {
    Add-Result "Key Vault accessible" $false "Error: $_. Check auth and firewall."
    if (-not $Preview) { exit 1 }
}

# PREVIEW MODE
if ($Preview) {
    Write-Host ""
    Write-Host "PROPOSED IMPORT (PREVIEW - NO CHANGES MADE)" -ForegroundColor Yellow
    Write-Host ("-" * 50) -ForegroundColor Yellow
    Write-Host "  Vault      : $VaultName"
    Write-Host "  Certificate: $CertName"
    Write-Host "  Expiry     : $ExpiryDate"
    Write-Host "  Thumbprint : $($Thumbprint.Substring(0,16))..."
    Write-Host ""
    Write-Host "To execute: .\Import-CertificateToKeyVault.ps1 -VaultName $VaultName -CertName $CertName -PfxPath $PfxPath -Execute"
    exit 0
}

# DRY-RUN MODE
if ($DryRun) {
    Write-Host ""
    Write-Host "[DRY-RUN] Would execute:" -ForegroundColor DarkYellow
    Write-Host "  Import-AzKeyVaultCertificate -VaultName $VaultName -Name $CertName -FilePath $PfxPath" -ForegroundColor DarkYellow
    Write-Host ""
    Write-Host "[DRY-RUN] No changes made. Run with -Execute to perform the actual import." -ForegroundColor DarkYellow
    exit 0
}

# EXECUTE MODE - Approval Gate
if ($Execute) {
    Write-Host ""
    Write-Host ("=" * 70) -ForegroundColor Red
    Write-Host " APPROVAL GATE" -ForegroundColor Red
    Write-Host ("=" * 70) -ForegroundColor Red
    Write-Host ""
    Write-Host "  PROPOSED IMPORT:" -ForegroundColor White
    Write-Host "  Vault      : $VaultName"
    Write-Host "  Certificate: $CertName"
    Write-Host "  Expiry     : $ExpiryDate"
    Write-Host "  Thumbprint : $($Thumbprint.Substring(0,16))..."
    Write-Host ""
    Write-Host "  WARNING: This will import into PRODUCTION Key Vault." -ForegroundColor Yellow
    Write-Host ""
    $Confirm = Read-Host "  Type CONFIRM to proceed (anything else cancels)"
    if ($Confirm -ne "CONFIRM") {
        Write-Host ""
        Write-Host "Import cancelled. Got: $Confirm" -ForegroundColor Yellow
        exit 0
    }
    Write-Host "  Approval granted. Proceeding with import." -ForegroundColor Green
    Write-Host ""
    
    # Execute import
    try {
        Write-Host "Importing certificate..." -ForegroundColor White
        if ($PfxPassword) {
            $Imported = Import-AzKeyVaultCertificate -VaultName $VaultName -Name $CertName -FilePath $PfxPath -Password $PfxPassword
        } else {
            $Imported = Import-AzKeyVaultCertificate -VaultName $VaultName -Name $CertName -FilePath $PfxPath
        }
        Write-Host ""
        Write-Host "SUCCESS: Certificate imported successfully." -ForegroundColor Green
        Write-Host "  Vault  : $VaultName" -ForegroundColor Gray
        Write-Host "  Name   : $CertName" -ForegroundColor Gray
        Write-Host "  Version: $($Imported.Version)" -ForegroundColor Gray
        Write-Host ""
        Write-Host "NEXT STEPS:" -ForegroundColor White
        Write-Host "  1. Run Invoke-PostImportValidation.ps1 to validate the import" -ForegroundColor Gray
        Write-Host "  2. Verify App Service is serving the new certificate" -ForegroundColor Gray
        Write-Host "  3. Update Jira ticket" -ForegroundColor Gray
    } catch {
        Write-Host ""
        Write-Error "Import FAILED: $_"
        Write-Host "See TROUBLESHOOTING.md for common import errors." -ForegroundColor Yellow
        exit 1
    }
}

$Duration = [int]((Get-Date) - $StartTime).TotalSeconds
Write-Host "Duration: ${Duration}s" -ForegroundColor Gray
