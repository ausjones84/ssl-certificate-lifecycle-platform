# New-PfxPackage.ps1 - Phase 3: Package certificate and private key as PFX
# Usage: .\New-PfxPackage.ps1 -CertPath fullchain.pem -KeyPath king5.key

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$CertPath,
    [Parameter(Mandatory=$true)][string]$KeyPath,
    [string]$OutputPath='',
    [string]$Password=''
)
$ErrorActionPreference='Stop'

# Validate OpenSSL
if(-not(Get-Command openssl -ErrorAction SilentlyContinue)){Write-Error 'OpenSSL not found. Install from https://slproweb.com/products/Win32OpenSSL.html';exit 1}
if(-not(Test-Path $CertPath)){Write-Error "Cert not found: $CertPath";exit 1}
if(-not(Test-Path $KeyPath)){Write-Error "Key not found: $KeyPath";exit 1}

if($OutputPath-eq''){$OutputPath=Join-Path([IO.Path]::GetDirectoryName($CertPath))([IO.Path]::GetFileNameWithoutExtension($CertPath)+'.pfx')}

Write-Host 'Creating PFX package...' -ForegroundColor Cyan
Write-Host "  Cert: $CertPath" -ForegroundColor Gray
Write-Host "  Key : $KeyPath" -ForegroundColor Gray
Write-Host "  Out : $OutputPath" -ForegroundColor Gray

$args2 = @('pkcs12','-export','-in',$CertPath,'-inkey',$KeyPath,'-out',$OutputPath)
if($Password-ne''){$args2+=@('-passout',"pass:$Password")}else{$args2+=@('-passout','pass:')}
& openssl @args2 2>&1 | Out-Null
if($LASTEXITCODE-ne 0){Write-Error 'PFX creation failed';exit 1}

# Validate PFX
Write-Host 'Validating PFX...' -ForegroundColor White
$valArgs = @('pkcs12','-info','-in',$OutputPath,'-noout')
if($Password-ne''){$valArgs+=@('-passin',"pass:$Password")}else{$valArgs+=@('-passin','pass:')}
$valOut = & openssl @valArgs 2>&1
if($LASTEXITCODE-eq 0){
    Write-Host "  [PASS] PFX is valid" -ForegroundColor Green
    Write-Host "`nPFX created: $OutputPath" -ForegroundColor Green
    Write-Host 'NEXT: Import-CertificateToKeyVault.ps1 --Preview' -ForegroundColor White
} else {
    Write-Warning "PFX validation warning: $valOut"
}
