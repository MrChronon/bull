[CmdletBinding()]
param(
    [ValidateSet('Client','Server','AllInOne')][string]$Role = '',
    [ValidateSet('lan','overlay','direct')][string]$Route = 'overlay',
    [ValidateRange(1,65535)][int]$EndpointPort = 22,
    [string]$SshUser = $env:USERNAME,
    [switch]$InstallDependencies,
    [switch]$InstallTailscale,
    [string]$AuthorizedKeyPath = '',
    [string]$PublicHost = '',
    [string]$ConnectionOutput = '',
    [string]$ConnectionBundle = '',
    [string]$IdentityFile = '',
    [string]$ShortcutDesktop = '',
    [string]$ShortcutPrograms = '',
    [switch]$GenerateClientKey,
    [switch]$NoKeyPassphrase,
    [switch]$NonInteractive
)

$ErrorActionPreference = 'Stop'
$base = $PSScriptRoot
$client = Join-Path $base 'bull_client_v0.24.0.0.py'
$shortcut = Join-Path $base 'Install-BULL-v0.24.0.0-Shortcut.ps1'
$nodeInstaller = Join-Path $base 'Server\Install-BULL-Node.ps1'
$keyInstaller = Join-Path $base 'Client\New-BULL-ClientKey.ps1'

function Resolve-Python {
    $python = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($python) { return $python.Source }
    $py = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($py) { return $py.Source }
    if (-not $InstallDependencies) { throw 'Python 3 not found. Re-run with -InstallDependencies.' }
    $winget = Get-Command winget.exe -ErrorAction SilentlyContinue
    if (-not $winget) { throw 'winget is required for automatic Python installation.' }
    & $winget.Source install --id Python.Python.3.12 --exact --accept-source-agreements --accept-package-agreements --silent
    if ($LASTEXITCODE -ne 0) { throw "Python installation failed (exit $LASTEXITCODE)." }
    $python = Get-Command python.exe -ErrorAction SilentlyContinue
    if (-not $python) { throw 'Python was installed but is not visible yet. Open a new terminal and run installer again.' }
    return $python.Source
}

if (-not $Role) {
    if ($NonInteractive) { throw '-Role is required with -NonInteractive.' }
    Write-Host 'BULL v0.24.0.0 platform installer' -ForegroundColor Green
    Write-Host '  1. Client      - connect to local or remote models'
    Write-Host '  2. Server      - OpenSSH + Ollama test node'
    Write-Host '  3. AllInOne    - client and local server on this PC'
    $choice = Read-Host 'Role [1-3]'
    $Role = @{'1'='Client';'2'='Server';'3'='AllInOne'}[$choice]
    if (-not $Role) { throw 'Unknown role.' }
}

if ($Role -eq 'Server' -and -not $AuthorizedKeyPath) {
    if ($NonInteractive) { throw '-AuthorizedKeyPath is required for the Server role.' }
    $AuthorizedKeyPath = Read-Host 'Path to the client public key (.pub)'
    if (-not $AuthorizedKeyPath) {
        throw 'Server setup was cancelled: a client public key is required.'
    }
}
if ($Role -eq 'AllInOne' -and -not $AuthorizedKeyPath) {
    Write-Host 'AllInOne will use a safe local-only node. SSH remains disabled until a public key is supplied.' -ForegroundColor Cyan
}

if ($Role -in @('Server','AllInOne') -and $AuthorizedKeyPath -and -not $NonInteractive -and -not $PublicHost) {
    Write-Host ''
    Write-Host 'How will the Client reach this server?' -ForegroundColor Cyan
    Write-Host '  1. Private VPN / Tailscale (recommended)'
    Write-Host '  2. Internet via public IP and router port forwarding'
    Write-Host '  3. Local network only'
    $routeChoice = Read-Host 'Connection route [1-3]'
    $Route = @{'1'='overlay';'2'='direct';'3'='lan'}[$routeChoice]
    if (-not $Route) { throw 'Unknown connection route.' }
    if ($Route -eq 'direct') {
        $PublicHost = (Read-Host 'Public IPv4 address or DNS name').Trim()
        if (-not $PublicHost) { throw 'PublicHost is required for direct Internet access.' }
        $portText = (Read-Host 'External TCP port on the router [48222]').Trim()
        $EndpointPort = if ($portText) { [int]$portText } else { 48222 }
        if ($EndpointPort -lt 1 -or $EndpointPort -gt 65535) { throw 'EndpointPort must be 1..65535.' }
    } elseif ($Route -eq 'overlay') {
        $PublicHost = (Read-Host 'VPN IP or DNS name').Trim()
        if (-not $PublicHost) { throw 'VPN IP or DNS name is required for the connection bundle.' }
    } else {
        $PublicHost = $env:COMPUTERNAME
    }
}

if ($Role -in @('Server','AllInOne')) {
    $principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        if ($NonInteractive) { throw 'Server and AllInOne roles require administrator rights.' }
        Write-Host 'Requesting administrator rights for the server role...' -ForegroundColor Yellow
        $elevated = @('-NoLogo','-NoProfile','-ExecutionPolicy','Bypass','-File',('"'+$PSCommandPath+'"'),'-Role',$Role)
        if ($InstallDependencies) { $elevated += '-InstallDependencies' }
        if ($InstallTailscale) { $elevated += '-InstallTailscale' }
        if ($AuthorizedKeyPath) { $elevated += @('-AuthorizedKeyPath',('"'+$AuthorizedKeyPath+'"')) }
        if ($PublicHost) { $elevated += @('-PublicHost',('"'+$PublicHost+'"')) }
        $elevated += @('-Route',$Route,'-EndpointPort',$EndpointPort,'-SshUser',$SshUser)
        if ($ConnectionOutput) { $elevated += @('-ConnectionOutput',('"'+$ConnectionOutput+'"')) }
        $process = Start-Process -FilePath 'powershell.exe' -Verb RunAs -ArgumentList $elevated -Wait -PassThru
        exit $process.ExitCode
    }
}

$python = $null
if ($Role -in @('Client','AllInOne')) {
    $python = Resolve-Python
    $shortcutArgs = @('-NoLogo','-NoProfile','-ExecutionPolicy','Bypass','-File',$shortcut,'-Quiet')
    if ($ShortcutDesktop) { $shortcutArgs += @('-DesktopDirectory',$ShortcutDesktop) }
    if ($ShortcutPrograms) { $shortcutArgs += @('-ProgramsDirectory',$ShortcutPrograms) }
    & powershell.exe @shortcutArgs
    if ($LASTEXITCODE -ne 0) { throw 'Shortcut installation failed.' }
    if ($GenerateClientKey) {
        $keyArgs = @('-NoLogo','-NoProfile','-ExecutionPolicy','Bypass','-File',$keyInstaller)
        if ($NoKeyPassphrase) { $keyArgs += '-NoPassphrase' }
        if ($NonInteractive) { $keyArgs += '-NonInteractive' }
        & powershell.exe @keyArgs
        if ($LASTEXITCODE -ne 0) { throw 'Client SSH key generation failed.' }
    }
}

if ($Role -in @('Server','AllInOne')) {
    $nodeArgs = @('-NoLogo','-NoProfile','-ExecutionPolicy','Bypass','-File',$nodeInstaller,'-InstallOllama')
    $nodeArgs += @('-Route',$Route,'-EndpointPort',$EndpointPort,'-SshUser',$SshUser)
    if ($Role -eq 'AllInOne' -and -not $AuthorizedKeyPath) { $nodeArgs += '-LocalOnly' }
    if ($InstallTailscale) { $nodeArgs += '-InstallTailscale' }
    if ($AuthorizedKeyPath) { $nodeArgs += @('-AuthorizedKeyPath',$AuthorizedKeyPath) }
    if ($PublicHost) { $nodeArgs += @('-PublicHost',$PublicHost) }
    if ($ConnectionOutput) { $nodeArgs += @('-ConnectionOutput',$ConnectionOutput) }
    if ($NonInteractive) { $nodeArgs += '-NonInteractive' }
    & powershell.exe @nodeArgs
    if ($LASTEXITCODE -ne 0) { throw 'Server node installation failed.' }
}

if ($Role -eq 'AllInOne') {
    & $python $client --use-local
    if ($LASTEXITCODE -ne 0) { throw 'Cannot select local backend.' }
}

if ($Role -eq 'Client' -and ($ConnectionBundle -or $IdentityFile)) {
    if (-not $ConnectionBundle -or -not $IdentityFile) {
        throw '-ConnectionBundle and -IdentityFile must be provided together.'
    }
    & $python $client --import-connection $ConnectionBundle $IdentityFile
    if ($LASTEXITCODE -ne 0) { throw 'Connection import failed.' }
}

Write-Host "BULL role $Role configured." -ForegroundColor Green
if ($Role -eq 'Client' -and -not $ConnectionBundle) {
    Write-Host 'Open Backend -> Choose Lab to use local Ollama or import a server connection.' -ForegroundColor Cyan
}
