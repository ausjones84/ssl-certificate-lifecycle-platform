# Test-CertificateEndpoint.ps1 - Test HTTPS endpoint and live certificate
# Usage: .\Test-CertificateEndpoint.ps1 -Hostname king5.com

[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$Hostname,[int]$Port=443)
$ErrorActionPreference='Stop'

Write-Host "Testing HTTPS: $Hostname:$Port" -ForegroundColor Cyan

# Test HTTP response
try{
    $r=Invoke-WebRequest -Uri "https://$Hostname" -UseBasicParsing -TimeoutSec 15 -ErrorAction Stop
    Write-Host "  [PASS] HTTPS endpoint: HTTP $($r.StatusCode)" -ForegroundColor Green
}catch{
    Write-Host "  [FAIL] HTTPS endpoint: $_" -ForegroundColor Red
}

# Test live certificate
try{
    $tcp=[System.Net.Sockets.TcpClient]::new($Hostname,$Port)
    $ssl=[System.Net.Security.SslStream]::new($tcp.GetStream(),$false,{$true})
    $ssl.AuthenticateAsClient($Hostname)
    $cert=[System.Security.Cryptography.X509Certificates.X509Certificate2]::new($ssl.RemoteCertificate)
    $days=[int]($cert.NotAfter-(Get-Date)).TotalDays
    Write-Host "  [PASS] Certificate presented" -ForegroundColor Green
    Write-Host "    Subject: $($cert.Subject)" -ForegroundColor Gray
    Write-Host "    Issuer : $($cert.Issuer)" -ForegroundColor Gray
    Write-Host "    Expiry : $($cert.NotAfter.ToString('yyyy-MM-dd')) ($days days)" -ForegroundColor $(if($days-lt30){'Yellow'}else{'Gray'})
    Write-Host "    Thumb  : $($cert.Thumbprint.Substring(0,16))..." -ForegroundColor Gray
    $ssl.Dispose();$tcp.Dispose()
}catch{
    Write-Host "  [FAIL] Certificate check: $_" -ForegroundColor Red
}
