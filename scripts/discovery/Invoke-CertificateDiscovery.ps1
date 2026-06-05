<#
.SYNOPSIS
    Phase 1: SSL Certificate Discovery - Scans Azure Key Vaults and App Services.

.DESCRIPTION
    Discovers all certificates in Key Vaults and maps them to App Service SSL bindings.
    Outputs CertificateInventory.csv and CertificateInventory.md to the reports/ directory.

.PARAMETER SubscriptionId
    Azure subscription ID. Uses current context if not provided.
.PARAMETER ResourceGroupName
    Optional: limit scan to a specific resource group.
.PARAMETER OutputDir
    Output directory (default: reports/)

.EXAMPLE
    .\Invoke-CertificateDiscovery.ps1 -SubscriptionId "xxx-yyy-zzz"
.EXAMPLE
    .\Invoke-CertificateDiscovery.ps1 -ResourceGroupName "rg-king-production" -OutputDir "C:\reports"
#>

[CmdletBinding()]
param (
    [Parameter(Mandatory = $false)][string]$SubscriptionId = "",
    [Parameter(Mandatory = $false)][string]$ResourceGroupName = "",
    [Parameter(Mandatory = $false)][string]$OutputDir = "reports"
)

$ErrorActionPreference = "Stop"
$StartTime = Get-Date
$Records = @()

function Get-DaysUntilExpiry { param([DateTime]$ExpiryDate)
    return [int]($ExpiryDate - (Get-Date)).TotalDays }

function Get-RiskLevel { param([int]$Days)
    if ($Days -lt 0) { return "EXPIRED" }
    if ($Days -le 14) { return "CRITICAL" }
    if ($Days -le 30) { return "HIGH" }
    if ($Days -le 60) { return "MEDIUM" }
    if ($Days -le 90) { return "LOW" }
    return "OK" }

Write-Host "SSL Certificate Lifecycle Platform - Discovery" -ForegroundColor Cyan
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

if ($SubscriptionId) { Set-AzContext -SubscriptionId $SubscriptionId | Out-Null }
$Context = Get-AzContext
Write-Host "Subscription: $($Context.Subscription.Name)" -ForegroundColor Gray

# --- Discover Key Vaults ---
Write-Host "[1/3] Discovering Key Vaults..." -ForegroundColor White
$KeyVaults = if ($ResourceGroupName) { Get-AzKeyVault -ResourceGroupName $ResourceGroupName } else { Get-AzKeyVault }
Write-Host "  Key Vaults: $($KeyVaults.Count)" -ForegroundColor Gray

foreach ($Vault in $KeyVaults) {
    $VaultName = $Vault.VaultName
    $VaultRG = $Vault.ResourceGroupName
    Write-Host "  Processing: $VaultName" -ForegroundColor Gray
    try {
        $Certs = Get-AzKeyVaultCertificate -VaultName $VaultName
        foreach ($Cert in $Certs) {
            $Detail = Get-AzKeyVaultCertificate -VaultName $VaultName -Name $Cert.Name
            $Expiry = $Detail.Expires
            $Days = if ($Expiry) { Get-DaysUntilExpiry -ExpiryDate $Expiry } else { $null }
            $Risk = if ($null -ne $Days) { Get-RiskLevel -Days $Days } else { "UNKNOWN" }
            $Records += [PSCustomObject]@{
                CertName        = $Cert.Name
                KeyVault        = $VaultName
                ResourceGroup   = $VaultRG
                Subscription    = $Context.Subscription.Name
                AppService      = ""
                Domain          = ""
                Expiration      = if ($Expiry) { $Expiry.ToString("yyyy-MM-dd") } else { "Unknown" }
                DaysUntilExpiry = $Days
                RiskLevel       = $Risk
                Thumbprint      = $Detail.Thumbprint
                Enabled         = $Detail.Enabled
                Version         = $Detail.Version
                LastChecked     = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
            }
            $RiskColour = switch ($Risk) { "EXPIRED" {"Red"} "CRITICAL" {"Red"} "HIGH" {"Yellow"} default {"Green"} }
            Write-Host "    $($Cert.Name) | Exp: $($Records[-1].Expiration) | Risk: $Risk" -ForegroundColor $RiskColour
        }
    } catch { Write-Warning "Cannot access $VaultName : $_" }
}

# --- Discover App Services ---
Write-Host "[2/3] Discovering App Services..." -ForegroundColor White
$Apps = if ($ResourceGroupName) { Get-AzWebApp -ResourceGroupName $ResourceGroupName } else { Get-AzWebApp }
Write-Host "  App Services: $($Apps.Count)" -ForegroundColor Gray
foreach ($App in $Apps) {
    try {
        $AppConfig = Get-AzWebApp -ResourceGroupName $App.ResourceGroup -Name $App.Name
        foreach ($Binding in $AppConfig.HostNameSslStates) {
            if ($Binding.SslState -ne "Disabled" -and $Binding.Thumbprint) {
                foreach ($R in $Records) {
                    if ($R.Thumbprint -and $Binding.Thumbprint.Length -ge 8 -and $R.Thumbprint.StartsWith($Binding.Thumbprint.Substring(0,8))) {
                        $R.AppService = $App.Name
                        $R.Domain = $Binding.Name
                        break
                    }
                }
            }
        }
    } catch { Write-Warning "Cannot read $($App.Name): $_" }
}

# --- Generate Reports ---
Write-Host "[3/3] Generating reports..." -ForegroundColor White
$CsvPath = Join-Path $OutputDir "CertificateInventory.csv"
$Records | Export-Csv -Path $CsvPath -NoTypeInformation -Encoding UTF8
Write-Host "  CSV: $CsvPath" -ForegroundColor Gray

$MdPath = Join-Path $OutputDir "CertificateInventory.md"
$Md = "# Certificate Inventory`n`nGenerated: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")`nTotal: $($Records.Count)`n`n"
$Md += "| Certificate | Key Vault | App Service | Expires | Days | Risk |`n|---|---|---|---|---|---|`n"
foreach ($R in ($Records | Sort-Object DaysUntilExpiry)) {
    $Md += "| $($R.CertName) | $($R.KeyVault) | $($R.AppService) | $($R.Expiration) | $($R.DaysUntilExpiry) | $($R.RiskLevel) |`n"
}
Set-Content -Path $MdPath -Value $Md -Encoding UTF8
Write-Host "  MD:  $MdPath" -ForegroundColor Gray

# --- Summary ---
$Duration = [int]((Get-Date) - $StartTime).TotalSeconds
$CritCount = ($Records | Where-Object { $_.RiskLevel -in ("EXPIRED","CRITICAL","HIGH") }).Count
Write-Host "" 
Write-Host "DISCOVERY COMPLETE | Certs: $($Records.Count) | Critical/High: $CritCount | Duration: ${Duration}s" -ForegroundColor Cyan
