<#
.SYNOPSIS
    Build a full certificate chain from leaf certificate and intermediate CA files.
.DESCRIPTION
    Phase 3 - Certificate Processing.
    Concatenates leaf certificate with intermediate CA certificates to build
    a complete certificate chain. Validates the chain using OpenSSL.
.PARAMETER CertPath
    Path to the leaf/domain certificate file (.crt or .cer).
.PARAMETER IntermediatePath
    Path to the intermediate CA certificate file.
.PARAMETER OutputPath
    Output path for the full chain file. Defaults to chain.crt in same directory.
.PARAMETER SkipValidation
    Skip OpenSSL chain validation.
.EXAMPLE
    .\Build-CertificateChain.ps1 -CertPath .\example.com.crt -IntermediatePath .\intermediate.crt
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]  [string]$CertPath,
    [Parameter(Mandatory = $true)]  [string[]]$IntermediatePath,
    [Parameter(Mandatory = $false)] [string]$OutputPath = "",
    [Parameter(Mandatory = $false)] [switch]$SkipValidation
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Status {
    param([string]$Message, [string]$Level = "INFO")
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $col = switch ($Level) {
        "SUCCESS" { "Green" } "WARN" { "Yellow" } "ERROR" { "Red" } default { "Cyan" }
    }
    Write-Host "[$ts] [$Level] $Message" -ForegroundColor $col
}

if (-not (Test-Path $CertPath)) { Write-Status "Certificate file not found: $CertPath" "ERROR"; exit 1 }
foreach ($p in $IntermediatePath) {
    if (-not (Test-Path $p)) { Write-Status "Intermediate not found: $p" "ERROR"; exit 1 }
}

if ([string]::IsNullOrEmpty($OutputPath)) {
    $OutputPath = Join-Path (Split-Path -Parent (Resolve-Path $CertPath)) "chain.crt"
}

Write-Status "Building certificate chain" "INFO"
Write-Status "  Leaf: $CertPath" "INFO"
foreach ($p in $IntermediatePath) { Write-Status "  Intermediate: $p" "INFO" }
Write-Status "  Output: $OutputPath" "INFO"

$chain = @()
$chain += (Get-Content -Path $CertPath -Raw).TrimEnd()
foreach ($p in $IntermediatePath) { $chain += (Get-Content -Path $p -Raw).TrimEnd() }
$chain -join "`n" | Set-Content -Path $OutputPath -Encoding ASCII
Write-Status "Chain file written: $OutputPath" "SUCCESS"

if (-not $SkipValidation) {
    if ($null -eq (Get-Command openssl -ErrorAction SilentlyContinue)) {
        Write-Status "OpenSSL not found. Skipping validation." "WARN"
    } else {
        $r = & openssl verify -CAfile $OutputPath $CertPath 2>&1
        if ($LASTEXITCODE -eq 0) { Write-Status "Chain validation PASSED" "SUCCESS" }
        else { Write-Status "Chain validation WARNING: $r" "WARN" }
    }
}

$certCount = ((Get-Content $OutputPath) | Select-String "BEGIN CERTIFICATE").Count
Write-Status "Certificates in chain: $certCount" "INFO"
Write-Status "Chain built successfully. Next: Run New-PfxPackage.ps1" "SUCCESS"# Build-CertificateChain.ps1
# Phase 3: Builds full certificate chain from individual cert files

[CmdletBinding()]
param (
    [Parameter(Mandatory = $true)][string]$CertPath,
    [Parameter(Mandatory = $false)][string]$IntermediatePath = '',
    [Parameter(Mandatory = $false)][string]$RootPath = '',
    [Parameter(Mandatory = $false)][string]$OutputPath = ''
)

$ErrorActionPreference = 'Stop'

function Get-CertPem { param([string]$Path)
    if (-not (Test-Path $Path)) { throw "File not found: $Path" }
    $content = Get-Content $Path -Raw
    if ($content -like '*BEGIN CERTIFICATE*') { return $content.Trim() }
    $bytes = [System.IO.File]::ReadAllBytes($Path)
    $b64 = [Convert]::ToBase64String($bytes)
    $lines = for ($i=0;$i -lt $b64.Length;$i+=64){$b64.Substring($i,[Math]::Min(64,$b64.Length-$i))}
    return "-----BEGIN CERTIFICATE-----`n$($lines -join "`n")`n-----END CERTIFICATE-----"
}

Write-Host 'Building certificate chain...' -ForegroundColor Cyan
$ChainContent = Get-CertPem -Path $CertPath
Write-Host "  [1] End-entity: $([System.IO.Path]::GetFileName($CertPath))" -ForegroundColor Green

if ($IntermediatePath -ne '' -and (Test-Path $IntermediatePath)) {
    $ChainContent += "`n" + (Get-CertPem -Path $IntermediatePath)
    Write-Host "  [2] Intermediate: $([System.IO.Path]::GetFileName($IntermediatePath))" -ForegroundColor Green
}

if ($RootPath -ne '' -and (Test-Path $RootPath)) {
    $ChainContent += "`n" + (Get-CertPem -Path $RootPath)
    Write-Host "  [3] Root: $([System.IO.Path]::GetFileName($RootPath))" -ForegroundColor Green
}

if ($OutputPath -eq '') {
    $Dir = [System.IO.Path]::GetDirectoryName($CertPath)
    $Base = [System.IO.Path]::GetFileNameWithoutExtension($CertPath)
    $OutputPath = Join-Path $Dir "$Base-fullchain.pem"
}

Set-Content -Path $OutputPath -Value $ChainContent -Encoding UTF8
$Count = ([regex]::Matches($ChainContent, 'BEGIN CERTIFICATE')).Count
Write-Host "`nChain built: $OutputPath ($Count certs)" -ForegroundColor Green
Write-Host 'NEXT: Run New-PfxPackage.ps1' -ForegroundColor White
