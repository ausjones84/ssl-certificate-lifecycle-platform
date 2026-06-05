<#
.SYNOPSIS
    Phase 2: Generate a Certificate Signing Request (CSR).

.DESCRIPTION
    Generates a CSR using OpenSSL with the specified CN and SAN values.
    Saves CSR, private key, and OpenSSL config to OutputPath.
    The private key is NEVER stored in the repository or logs.

.PARAMETER CommonName
    Certificate Common Name, e.g. "*.king5.com"
.PARAMETER SubjectAltNames
    Optional SANs as comma-separated list, e.g. "king5.com,www.king5.com"
.PARAMETER Organization
    Organization name
.PARAMETER OutputPath
    Directory to save CSR artifacts
.PARAMETER KeySize
    RSA key size (default: 2048)

.EXAMPLE
    .\New-CertificateRequest.ps1 -CommonName "*.king5.com" -OutputPath "C:\certs\king5"
#>

[CmdletBinding()]
param (
    [Parameter(Mandatory = $true)][string]$CommonName,
    [Parameter(Mandatory = $false)][string]$SubjectAltNames = "",
    [Parameter(Mandatory = $false)][string]$Organization = "TEGNA Inc.",
    [Parameter(Mandatory = $false)][string]$OrganizationalUnit = "IT Operations",
    [Parameter(Mandatory = $false)][string]$Country = "US",
    [Parameter(Mandatory = $false)][string]$State = "Washington",
    [Parameter(Mandatory = $false)][string]$City = "Seattle",
    [Parameter(Mandatory = $false)][string]$OutputPath = ".",
    [Parameter(Mandatory = $false)][int]$KeySize = 2048
)

$ErrorActionPreference = "Stop"

# Validate OpenSSL is available
$OpenSSL = Get-Command "openssl" -ErrorAction SilentlyContinue
if (-not $OpenSSL) {
    Write-Error "OpenSSL not found. Install from https://slproweb.com/products/Win32OpenSSL.html"
    exit 1
}

# Create output directory
$SafeName = $CommonName -replace "[^a-zA-Z0-9-.]", "_"
$CertDir = Join-Path $OutputPath $SafeName
New-Item -ItemType Directory -Path $CertDir -Force | Out-Null

$KeyPath = Join-Path $CertDir "$SafeName.key"
$CsrPath = Join-Path $CertDir "$SafeName.csr"
$CnfPath = Join-Path $CertDir "openssl.cnf"

Write-Host "CSR Generation" -ForegroundColor Cyan
Write-Host "  CN  : $CommonName" -ForegroundColor Gray
Write-Host "  Org : $Organization" -ForegroundColor Gray
Write-Host "  Key : $KeySize bits" -ForegroundColor Gray
Write-Host "  Out : $CertDir" -ForegroundColor Gray
Write-Host ""

# Build OpenSSL config
$SanSection = ""
$SanList = ""
if ($SubjectAltNames -ne "") {
    $Sans = $SubjectAltNames -split "," | ForEach-Object { "DNS:" + $_.Trim() }
    if (-not $SubjectAltNames.Contains($CommonName.TrimStart("*."))) {
        $Dans = @("DNS:$CommonName") + $Sans
    } else { $Dans = @("DNS:$CommonName") + $Sans }
    $SanList = $Dans -join ", "
    $SanSection = "[SAN]`nsubjectAltName = $SanList"
}

$CnfContent = @"
[req]
default_bits = $KeySize
prompt = no
distinguished_name = dn
$(if ($SubjectAltNames) { "req_extensions = v3_req" } else { "" })

[dn]
CN = $CommonName
O = $Organization
OU = $OrganizationalUnit
C = $Country
ST = $State
L = $City

[v3_req]
subjectAltName = @san_list

[san_list]
$SanSection
"@
Set-Content -Path $CnfPath -Value $CnfContent -Encoding UTF8

# Generate private key (2048-bit RSA)
Write-Host "Generating private key ($KeySize bits)..." -ForegroundColor White
& openssl genrsa -out $KeyPath $KeySize 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) { Write-Error "Key generation failed"; exit 1 }
Write-Host "  [DONE] Private key generated (KEEP SECURE - NEVER SHARE)" -ForegroundColor Green

# Generate CSR
Write-Host "Generating CSR..." -ForegroundColor White
& openssl req -new -key $KeyPath -out $CsrPath -config $CnfPath 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) { Write-Error "CSR generation failed"; exit 1 }
Write-Host "  [DONE] CSR generated" -ForegroundColor Green

# Validate CSR
Write-Host "Validating CSR..." -ForegroundColor White
$CsrInfo = & openssl req -in $CsrPath -text -noout 2>&1
$CnCheck = $CsrInfo | Where-Object { $_ -match "Subject:.*CN" }
if ($CnCheck) {
    Write-Host "  [PASS] CN verified in CSR" -ForegroundColor Green
} else {
    Write-Warning "  [WARN] Could not verify CN in CSR — review manually"
}

# Output summary
Write-Host ""
Write-Host "CSR GENERATION COMPLETE" -ForegroundColor Cyan
Write-Host "  CSR File   : $CsrPath" -ForegroundColor Gray
Write-Host "  Key File   : $KeyPath (PRIVATE — KEEP SECURE)" -ForegroundColor Yellow
Write-Host "  Config     : $CnfPath" -ForegroundColor Gray
Write-Host ""
Write-Host "NEXT STEPS:" -ForegroundColor White
Write-Host "  1. Submit CSR to Sectigo: $(Get-Content $CsrPath -Raw | Select-String "BEGIN CERTIFICATE REQUEST" | Select-Object -First 1)" -ForegroundColor Gray
Write-Host "  2. Complete domain validation in Sectigo portal" -ForegroundColor Gray
Write-Host "  3. Download issued certificate files" -ForegroundColor Gray
Write-Host "  4. Run Build-CertificateChain.ps1 to assemble the chain" -ForegroundColor Gray
