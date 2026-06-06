<#
.SYNOPSIS Test an HTTPS endpoint and verify the live certificate.
.PARAMETER Hostname The hostname to test.
.PARAMETER ExpectedThumbprint The expected SHA1 thumbprint. Optional.
.PARAMETER Port HTTPS port. Defaults to 443.
.EXAMPLE .\Test-CertificateEndpoint.ps1 -Hostname "example.com"
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]  [string]$Hostname,
    [Parameter(Mandatory=$false)] [string]$ExpectedThumbprint = "",
    [Parameter(Mandatory=$false)] [int]$Port = 443,
    [Parameter(Mandatory=$false)] [int]$TimeoutSeconds = 30
)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
function Write-Status {
    param([string]$Msg, [string]$Lvl = "INFO")
    $c = switch($Lvl){"SUCCESS"{"Green"}"WARN"{"Yellow"}"ERROR"{"Red"}"FAIL"{"Red"}default{"Cyan"}}
    Write-Host "[$((Get-Date -Format "HH:mm:ss"))] [$Lvl] $Msg" -ForegroundColor $c
}
Write-Status "Testing https://$Hostname`:$Port"
try {
    $r = Invoke-WebRequest "https://$Hostname`:$Port" -TimeoutSec $TimeoutSeconds -UseBasicParsing -EA Stop
    Write-Status "HTTP $($r.StatusCode)" "SUCCESS"
} catch {
    if ($_.Exception.Response) {
        $c = [int]$_.Exception.Response.StatusCode
        if ($c -lt 500) { Write-Status "HTTP $c (acceptable)" "SUCCESS" }
        else { Write-Status "HTTP $c (server error)" "FAIL"; exit 1 }
    } else { Write-Status "Connection failed: $($_.Exception.Message)" "FAIL"; exit 1 }
}
if ($null -ne (Get-Command openssl -EA SilentlyContinue)) {
    $ci = & openssl s_client -connect "$Hostname`:$Port" -servername $Hostname 2>&1 | openssl x509 -noout -fingerprint -dates -subject 2>&1
    if ($LASTEXITCODE -eq 0) {
        $ci | % { Write-Status "  $_" }
        $fl = $ci | ? { $_ -match "Fingerprint" }
        if ($fl -and $ExpectedThumbprint) {
            $live = ($fl -split "=",2)[1].Trim().Replace(":","").ToUpper()
            $exp  = $ExpectedThumbprint.Replace(":","").Replace(" ","").ToUpper()
            if ($live -eq $exp) { Write-Status "Thumbprint MATCH" "SUCCESS" }
            else { Write-Status "MISMATCH Expected:$exp Live:$live" "FAIL"; exit 1 }
        }
    } else { Write-Status "Could not retrieve live cert via OpenSSL" "WARN" }
} else { Write-Status "OpenSSL not found - skipping live cert check" "WARN" }
Write-Status "Endpoint test complete." "SUCCESS"
