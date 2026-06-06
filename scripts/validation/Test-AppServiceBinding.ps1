<#
.SYNOPSIS Test Azure App Service SSL binding for a certificate.
.PARAMETER AppServiceName The App Service name to check.
.PARAMETER ExpectedThumbprint The expected certificate thumbprint. Optional.
.PARAMETER ResourceGroup Resource group of the App Service. Optional.
.EXAMPLE .\Test-AppServiceBinding.ps1 -AppServiceName "interactive-king5"
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]  [string]$AppServiceName,
    [Parameter(Mandatory=$false)] [string]$ExpectedThumbprint = "",
    [Parameter(Mandatory=$false)] [string]$ResourceGroup = ""
)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
function Write-Status {
    param([string]$Msg, [string]$Lvl = "INFO")
    $c = switch($Lvl){"SUCCESS"{"Green"}"WARN"{"Yellow"}"FAIL"{"Red"}default{"Cyan"}}
    Write-Host "[$((Get-Date -Format "HH:mm:ss"))] [$Lvl] $Msg" -ForegroundColor $c
}
Write-Status "Checking App Service SSL binding: $AppServiceName"
try {
    if ($ResourceGroup) { $app = az webapp show --name $AppServiceName --resource-group $ResourceGroup 2>&1 | ConvertFrom-Json }
    else { $app = az webapp show --name $AppServiceName 2>&1 | ConvertFrom-Json }
    if (-not $app) { Write-Status "App Service not found: $AppServiceName" "FAIL"; exit 1 }
    Write-Status "Found: $($app.name) in $($app.resourceGroup)" "SUCCESS"
} catch { Write-Status "Failed: $($_.Exception.Message)" "FAIL"; exit 1 }
try {
    $bindings = az webapp config ssl list --resource-group $app.resourceGroup 2>&1 | ConvertFrom-Json
    if ($bindings -and $bindings.Count -gt 0) {
        Write-Status "SSL certs in RG: $($bindings.Count)" "INFO"
        $bindings | % { Write-Status "  $($_.name) | $($_.thumbprint) | Expiry:$($_.expirationDate)" }
        if ($ExpectedThumbprint) {
            $exp = $ExpectedThumbprint.Replace(":","").Replace(" ","").ToUpper()
            $m = $bindings | ? { $_.thumbprint -and $_.thumbprint.ToUpper() -eq $exp }
            if ($m) { Write-Status "Binding FOUND for $exp" "SUCCESS" }
            else { Write-Status "Binding NOT FOUND for $exp" "FAIL"; exit 1 }
        }
    } else { Write-Status "No SSL certs found in resource group" "WARN" }
} catch { Write-Status "SSL binding check failed: $($_.Exception.Message)" "WARN" }
try {
    $hosts = az webapp config hostname list --webapp-name $AppServiceName --resource-group $app.resourceGroup 2>&1 | ConvertFrom-Json
    $hosts | % {
        if ($_.sslState -eq "SniEnabled") { Write-Status "SNI enabled: $($_.name)" "SUCCESS" }
        elseif ($_.sslState -eq "Disabled") { Write-Status "SSL disabled: $($_.name)" "WARN" }
    }
} catch { Write-Status "Could not retrieve hostname bindings." "WARN" }
Write-Status "App Service binding check completed." "SUCCESS"
