[CmdletBinding()]
param(
    [ValidateSet('overlay','direct')][string]$Route = 'direct',
    [string]$PublicHost = '',
    [ValidateRange(1,65535)][int]$EndpointPort = 48222,
    [string]$ServerLanAddress = ''
)

$ErrorActionPreference = 'Stop'
$failures = [Collections.Generic.List[string]]::new()

function Write-Check([bool]$Ok,[string]$Name,[string]$Detail) {
    $color = if ($Ok) { 'Green' } else { 'Red' }
    $mark = if ($Ok) { '[OK]' } else { '[FAIL]' }
    Write-Host ("{0,-7} {1}: {2}" -f $mark,$Name,$Detail) -ForegroundColor $color
    if (-not $Ok) { $failures.Add("$Name - $Detail") }
}

function Get-PrimaryLanAddress {
    if ($ServerLanAddress) { return $ServerLanAddress }
    try {
        $row = Get-NetIPConfiguration -ErrorAction Stop |
            Where-Object { $_.IPv4DefaultGateway -and $_.NetAdapter.Status -eq 'Up' } |
            Select-Object -First 1
        return [string]($row.IPv4Address.IPAddress | Select-Object -First 1)
    } catch {
        return ''
    }
}

Write-Host 'BULL remote readiness' -ForegroundColor Cyan
Write-Host 'This command changes nothing.' -ForegroundColor DarkGray
Write-Host ''

$service = Get-Service sshd -ErrorAction SilentlyContinue
Write-Check ([bool]$service) 'OpenSSH service' $(if ($service) { 'installed' } else { 'not installed' })
if ($service) {
    Write-Check ($service.Status -eq 'Running') 'sshd state' ([string]$service.Status)
    Write-Check ($service.StartType -eq 'Automatic') 'sshd startup' ([string]$service.StartType)
}

$sshd = Join-Path $env:WINDIR 'System32\OpenSSH\sshd.exe'
if (Test-Path -LiteralPath $sshd) {
    $effective = (& $sshd -T 2>$null) -join "`n"
    $lower = $effective.ToLowerInvariant()
    Write-Check ($lower -match '(?m)^passwordauthentication no$') 'SSH password login' 'must be disabled'
    Write-Check ($lower -match '(?m)^kbdinteractiveauthentication no$') 'SSH keyboard login' 'must be disabled'
    Write-Check ($lower -match '(?m)^authenticationmethods publickey$') 'SSH authentication' 'public key only'
} else {
    Write-Check $false 'sshd executable' 'not found'
}

$sshRule = Get-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -ErrorAction SilentlyContinue
Write-Check ([bool]$sshRule -and $sshRule.Enabled -eq 'True') 'Windows Firewall SSH' 'enabled for TCP 22'

$listeners = @(Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue)
$sshListener = $listeners | Where-Object { $_.LocalPort -eq 22 }
Write-Check ([bool]$sshListener) 'SSH listener' 'TCP 22'

foreach ($port in 11434,11435,8080) {
    $rows = @($listeners | Where-Object { $_.LocalPort -eq $port })
    $publicRows = @($rows | Where-Object { $_.LocalAddress -notin @('127.0.0.1','::1') })
    Write-Check ($publicRows.Count -eq 0) "Inference port $port" $(if ($rows.Count) { 'loopback only' } else { 'not listening' })
}

$lanAddress = Get-PrimaryLanAddress
Write-Check ([bool]$lanAddress) 'Server LAN address' $(if ($lanAddress) { $lanAddress } else { 'not detected' })

if ($Route -eq 'direct') {
    Write-Check ([bool]$PublicHost) 'Public host' $(if ($PublicHost) { 'configured' } else { 'required for direct route' })
    Write-Host ''
    Write-Host 'Router rule (manual):' -ForegroundColor Yellow
    Write-Host "  TCP $PublicHost`:$EndpointPort -> $lanAddress`:22"
    Write-Host '  Never forward 11434, 11435, 8080 or RDP.' -ForegroundColor Yellow
    Write-Host '  Test from mobile Internet, not from the same home Wi-Fi.' -ForegroundColor Cyan
}

Write-Host ''
if ($failures.Count) {
    Write-Host "NOT READY: $($failures.Count) blocking check(s). Do not open the router port yet." -ForegroundColor Red
    exit 1
}

Write-Host 'READY: local server checks passed. Complete and verify the router/VPN step separately.' -ForegroundColor Green
exit 0
