[CmdletBinding(SupportsShouldProcess=$true)]
param(
    [ValidateSet('lan','overlay','direct')][string]$Route = 'overlay',
    [string]$PublicHost = $env:COMPUTERNAME,
    [ValidateRange(1,65535)][int]$EndpointPort = 22,
    [string]$SshUser = $env:USERNAME,
    [string]$AuthorizedKeyPath = '',
    [string]$ConnectionId = 'bull-lab',
    [string]$ConnectionName = 'BULL Lab',
    [string]$ConnectionOutput = '',
    [switch]$InstallOllama,
    [switch]$InstallTailscale,
    [switch]$LocalOnly,
    [switch]$NonInteractive
)

$ErrorActionPreference = 'Stop'

function Assert-Administrator {
    $principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw 'Server installation requires an elevated PowerShell session.'
    }
}

function Assert-ConnectionParameters {
    if ($SshUser -notmatch '^[A-Za-z0-9._-]{1,64}$') {
        throw 'SshUser has an invalid format.'
    }
    if ($PublicHost -and ($PublicHost.StartsWith('-') -or $PublicHost -notmatch '^[A-Za-z0-9._:\[\]%-]+$')) {
        throw 'PublicHost must be an IPv4/IPv6 address or DNS name without spaces.'
    }
    if ($Route -eq 'direct' -and -not $PublicHost) {
        throw 'Direct Internet access requires an explicit -PublicHost value.'
    }
}

function Get-PrimaryLanAddress {
    try {
        $row = Get-NetIPConfiguration -ErrorAction Stop |
            Where-Object { $_.IPv4DefaultGateway -and $_.NetAdapter.Status -eq 'Up' } |
            Select-Object -First 1
        if ($row -and $row.IPv4Address.IPAddress) {
            return [string]($row.IPv4Address.IPAddress | Select-Object -First 1)
        }
    } catch {}
    return '<SERVER_LAN_IP>'
}

function Ensure-WindowsCapability([string]$Name) {
    $capability = Get-WindowsCapability -Online -Name $Name
    if ($capability.State -ne 'Installed') {
        if ($PSCmdlet.ShouldProcess($Name,'Install Windows capability')) {
            Add-WindowsCapability -Online -Name $Name | Out-Null
        }
    }
}

function Ensure-WingetPackage([string]$Id,[string]$CommandName) {
    if (Get-Command $CommandName -ErrorAction SilentlyContinue) { return }
    $winget = Get-Command winget.exe -ErrorAction SilentlyContinue
    if (-not $winget) { throw "winget is required to install $Id automatically." }
    if ($PSCmdlet.ShouldProcess($Id,'Install package with winget')) {
        & $winget.Source install --id $Id --exact --accept-source-agreements --accept-package-agreements --silent
        if ($LASTEXITCODE -ne 0) { throw "winget failed to install $Id (exit $LASTEXITCODE)." }
    }
}

function Read-AuthorizedKey([string]$Path) {
    $resolved = (Resolve-Path -LiteralPath $Path).Path
    if ((Get-Item -LiteralPath $resolved).Length -gt 16384) { throw 'Public key file is too large.' }
    $line = (Get-Content -LiteralPath $resolved -Raw -Encoding UTF8).Trim()
    if ($line -match '[\r\n]' -or $line -notmatch '^(ssh-ed25519|ecdsa-sha2-nistp256|ssh-rsa)[ \t]+[A-Za-z0-9+/=]+(?:[ \t]+[^\r\n]*)?$') {
        throw 'AuthorizedKeyPath must contain one OpenSSH public key.'
    }
    return $line
}

function Install-AuthorizedKey([string]$Path) {
    if (-not $Path) { return }
    $line = Read-AuthorizedKey $Path
    $adminNames = @(Get-LocalGroupMember -SID 'S-1-5-32-544' -ErrorAction Stop | ForEach-Object { ($_.Name -split '\\')[-1] })
    $isAdmin = $adminNames -contains $SshUser
    if ($isAdmin) {
        $auth = Join-Path $env:ProgramData 'ssh\administrators_authorized_keys'
    } else {
        $profileRoot = Split-Path $env:USERPROFILE -Parent
        $userProfile = Join-Path $profileRoot $SshUser
        if (-not (Test-Path -LiteralPath $userProfile)) { throw "Windows user profile not found: $userProfile" }
        $auth = Join-Path $userProfile '.ssh\authorized_keys'
    }
    $parent = Split-Path -Parent $auth
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
    $existing = if (Test-Path -LiteralPath $auth) { Get-Content -LiteralPath $auth -Encoding UTF8 } else { @() }
    if ($existing -notcontains $line) { Add-Content -LiteralPath $auth -Value $line -Encoding UTF8 }
    if ($isAdmin) {
        & icacls.exe $auth /inheritance:r /grant:r '*S-1-5-18:F' /grant:r '*S-1-5-32-544:F' | Out-Null
    } else {
        $userSid = (Get-LocalUser -Name $SshUser -ErrorAction Stop).SID.Value
        & icacls.exe $auth /inheritance:r /grant:r '*S-1-5-18:F' /grant:r "*$userSid`:F" | Out-Null
    }
    if ($LASTEXITCODE -ne 0) { throw 'Failed to secure administrators_authorized_keys ACL.' }
}

function Set-KeyOnlySshForUser([string]$User) {
    if ($User -notmatch '^[A-Za-z0-9._-]{1,64}$') { throw 'SshUser has an invalid format.' }
    $config = Join-Path $env:ProgramData 'ssh\sshd_config'
    if (-not (Test-Path -LiteralPath $config)) { throw "sshd_config not found: $config" }
    $begin = "# BEGIN BULL KEY-ONLY $User"
    $end = "# END BULL KEY-ONLY $User"
    $raw = Get-Content -LiteralPath $config -Raw -Encoding UTF8
    $escapedBegin = [regex]::Escape($begin); $escapedEnd = [regex]::Escape($end)
    $raw = [regex]::Replace($raw,"(?ms)^$escapedBegin\r?\n.*?^$escapedEnd\r?\n?",'')
    $globalBegin = '# BEGIN BULL GLOBAL KEY-ONLY'
    $globalEnd = '# END BULL GLOBAL KEY-ONLY'
    $escapedGlobalBegin = [regex]::Escape($globalBegin)
    $escapedGlobalEnd = [regex]::Escape($globalEnd)
    $raw = [regex]::Replace($raw,"(?ms)^$escapedGlobalBegin\r?\n.*?^$escapedGlobalEnd\r?\n?",'')
    # Enforce key-only authentication globally. Remove active occurrences first
    # so an earlier PasswordAuthentication=yes cannot win by sshd's first-value rule.
    $raw = [regex]::Replace(
        $raw,
        '(?mi)^\s*(?:PubkeyAuthentication|PasswordAuthentication|KbdInteractiveAuthentication|AuthenticationMethods)\s+[^#\r\n]*(?:\r?\n|$)',
        ''
    )
    $global = @"
$globalBegin
PubkeyAuthentication yes
PasswordAuthentication no
KbdInteractiveAuthentication no
AuthenticationMethods publickey
GatewayPorts no
$globalEnd
"@
$block = @"
$begin
Match User $User
    PubkeyAuthentication yes
    PasswordAuthentication no
    KbdInteractiveAuthentication no
    AllowTcpForwarding local
    X11Forwarding no
    PermitTunnel no
$end
"@
    $tmp = $config+'.bull.tmp'
    ($global.Trim()+"`r`n`r`n"+$raw.Trim()+"`r`n`r`n"+$block.Trim()+"`r`n") | Set-Content -LiteralPath $tmp -Encoding UTF8
    & "$env:WINDIR\System32\OpenSSH\sshd.exe" -t -f $tmp
    if ($LASTEXITCODE -ne 0) { Remove-Item -LiteralPath $tmp -Force; throw 'Generated sshd_config failed validation.' }
    if (-not (Test-Path -LiteralPath ($config+'.pre-bull.bak'))) {
        Copy-Item -LiteralPath $config -Destination ($config+'.pre-bull.bak')
    }
    Move-Item -LiteralPath $tmp -Destination $config -Force
    Restart-Service sshd
}

function New-ConnectionBundle {
    $hostKey = Join-Path $env:ProgramData 'ssh\ssh_host_ed25519_key.pub'
    if (-not (Test-Path -LiteralPath $hostKey)) { throw "OpenSSH host public key not found: $hostKey" }
    $hostPublicKey = (Get-Content -LiteralPath $hostKey -Raw -Encoding ASCII).Trim()
    $fingerprintLine = (& ssh-keygen.exe -lf $hostKey -E sha256 | Select-Object -First 1)
    if ($fingerprintLine -notmatch '(SHA256:[A-Za-z0-9+/=]+)') { throw 'Cannot calculate SSH host-key fingerprint.' }
    $fingerprint = $Matches[1]
    $safeId = $ConnectionId.ToLowerInvariant()
    if ($safeId -notmatch '^[a-z0-9][a-z0-9._-]{0,63}$') { throw 'ConnectionId has an invalid format.' }
    $output = if ($ConnectionOutput) { $ConnectionOutput } else { Join-Path $PSScriptRoot "$safeId.connection.json" }
    $document = [ordered]@{
        schema = 'bull-connection'
        version = 1
        id = $safeId
        name = $ConnectionName
        route = $Route
        transport = 'ssh'
        endpoint = [ordered]@{ host = $PublicHost; port = $EndpointPort; user = $SshUser }
        backend = [ordered]@{ type = 'ollama'; remote_port = 11434 }
        host_public_key = $hostPublicKey
        host_key_fingerprint = $fingerprint
    }
    $document | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $output -Encoding UTF8
    return (Resolve-Path -LiteralPath $output).Path
}

Assert-ConnectionParameters
if (-not $LocalOnly -and -not $AuthorizedKeyPath) {
    throw 'Remote Server installation requires -AuthorizedKeyPath. Use -LocalOnly for a loopback-only node.'
}
# Gate the entire workflow, including service/firewall/config writes. Helper-level
# ShouldProcess checks alone do not protect the remaining operations under -WhatIf.
if (-not $PSCmdlet.ShouldProcess('BULL node', 'Configure services, authentication, firewall and packages')) { return }
Assert-Administrator
if (-not $LocalOnly) {
    Read-AuthorizedKey $AuthorizedKeyPath | Out-Null
    Get-LocalUser -Name $SshUser -ErrorAction Stop | Out-Null
}

if (-not $LocalOnly) {
    Ensure-WindowsCapability 'OpenSSH.Server~~~~0.0.1.0'
    Ensure-WindowsCapability 'OpenSSH.Client~~~~0.0.1.0'

    Set-Service -Name sshd -StartupType Automatic
    Start-Service -Name sshd
    if (-not (Get-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -ErrorAction SilentlyContinue)) {
        New-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -DisplayName 'OpenSSH Server (sshd)' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22 | Out-Null
    } else {
        Set-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -Enabled True -Action Allow | Out-Null
    }
    Install-AuthorizedKey $AuthorizedKeyPath
    Set-KeyOnlySshForUser $SshUser
}

if ($InstallTailscale) { Ensure-WingetPackage 'Tailscale.Tailscale' 'tailscale' }
if ($InstallOllama) {
    Ensure-WingetPackage 'Ollama.Ollama' 'ollama'
    [Environment]::SetEnvironmentVariable('OLLAMA_HOST','127.0.0.1:11434','Machine')
    $env:OLLAMA_HOST = '127.0.0.1:11434'
    if (-not (Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort 11434 -State Listen -ErrorAction SilentlyContinue)) {
        $ollama = (Get-Command ollama -ErrorAction Stop).Source
        Start-Process -FilePath $ollama -ArgumentList 'serve' -WindowStyle Hidden
    }
}

if ($LocalOnly) {
    Write-Host 'BULL loopback node is ready. SSH and inbound firewall rules were not enabled.' -ForegroundColor Green
    exit 0
}

$connection = New-ConnectionBundle
Write-Host 'BULL server node is ready.' -ForegroundColor Green
Write-Host "Connection bundle: $connection" -ForegroundColor Cyan
Write-Host 'Only SSH is opened in Windows Firewall. Ollama remains on loopback.' -ForegroundColor Green
if ($Route -eq 'direct') {
    $lanAddress = Get-PrimaryLanAddress
    Write-Host ''
    Write-Host 'Router action required (the installer never changes router settings automatically):' -ForegroundColor Yellow
    Write-Host "  Reserve LAN address: $lanAddress"
    Write-Host "  Forward TCP $PublicHost`:$EndpointPort -> $lanAddress`:22"
    Write-Host '  Do NOT forward 11434, 8080, 11435 or RDP.' -ForegroundColor Yellow
    Write-Host '  Test from mobile Internet; a same-LAN test may fail when NAT loopback is disabled.' -ForegroundColor Cyan
    $readiness = Join-Path $PSScriptRoot 'Test-BULL-RemoteReadiness.ps1'
    if (Test-Path -LiteralPath $readiness) {
        & powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File $readiness `
            -Route direct -PublicHost $PublicHost -EndpointPort $EndpointPort -ServerLanAddress $lanAddress
        if ($LASTEXITCODE -ne 0) {
            throw 'Direct Internet readiness failed. Do not open the router port until every blocking check passes.'
        }
    }
}
