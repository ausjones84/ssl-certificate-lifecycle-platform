# Test-AppServiceBinding.ps1 - Validate App Service SSL binding
# Usage: .\Test-AppServiceBinding.ps1 -AppServiceName interactive-king5 -ResourceGroupName rg-king-production

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$AppServiceName,
    [Parameter(Mandatory=$true)][string]$ResourceGroupName,
    [string]$ExpectedThumbprint=''
)
$ErrorActionPreference='Stop'

Write-Host "Testing App Service Binding: $AppServiceName" -ForegroundColor Cyan

try{
    $app=Get-AzWebApp -ResourceGroupName $ResourceGroupName -Name $AppServiceName
    $bindings=$app.HostNameSslStates|Where-Object{$_.SslState-ne'Disabled'}
    
    if($bindings.Count-gt 0){
        Write-Host "  [PASS] SSL bindings found: $($bindings.Count)" -ForegroundColor Green
        foreach($b in $bindings){
            Write-Host "    Host: $($b.Name) | State: $($b.SslState) | Thumb: $($b.Thumbprint.Substring(0,[Math]::Min(16,$b.Thumbprint.Length)))..." -ForegroundColor Gray
            if($ExpectedThumbprint-ne'' -and $b.Thumbprint){
                $match=$b.Thumbprint-like"$($ExpectedThumbprint.Substring(0,[Math]::Min(8,$ExpectedThumbprint.Length)))*"
                if($match){Write-Host "    [PASS] Thumbprint matches expected" -ForegroundColor Green}
                else{Write-Host "    [WARN] Thumbprint mismatch" -ForegroundColor Yellow}
            }
        }
    }else{
        Write-Host "  [FAIL] No SSL bindings found on $AppServiceName" -ForegroundColor Red
    }
}catch{
    Write-Host "  [FAIL] Cannot query App Service $AppServiceName : $_" -ForegroundColor Red
}
