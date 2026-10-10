[CmdletBinding()]
param([ValidateSet('client','benchmark','agent')][string]$Surface = 'client')

$ErrorActionPreference = "Stop"
$Host.UI.RawUI.WindowTitle = "BULL - Benchmark Lab"
Set-Location -LiteralPath $PSScriptRoot

# Force one Unicode encoding across Windows PowerShell, Python and child test processes.
try {
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [Console]::OutputEncoding = $utf8NoBom
    [Console]::InputEncoding = $utf8NoBom
    $OutputEncoding = $utf8NoBom
} catch {}
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"


# Best-effort console sizing. Windows Terminal may manage its own size and ignore this.
try {
    $raw = $Host.UI.RawUI
    $max = $raw.MaxPhysicalWindowSize
    $w = [Math]::Min(120, $max.Width)
    $h = [Math]::Min(52, $max.Height)
    $buf = $raw.BufferSize
    if ($buf.Width -lt $w) { $buf.Width = $w }
    if ($buf.Height -lt 5000) { $buf.Height = 5000 }
    $raw.BufferSize = $buf
    $win = $raw.WindowSize
    $win.Width = $w
    $win.Height = $h
    $raw.WindowSize = $win
} catch {}

$client = Join-Path $PSScriptRoot "bull_client_v0.29.0.1.py"
if ($Surface -eq 'benchmark') { $client = Join-Path $PSScriptRoot 'Apps\benchmark_lab_v0_29_0_1.py' }
elseif ($Surface -eq 'agent') { $client = Join-Path $PSScriptRoot 'Apps\agent_benchmark_v0_29_0_1.py' }
if (-not (Test-Path $client)) {
    Write-Host "ERROR: bull_client_v0.29.0.1.py not found." -ForegroundColor Red
    Read-Host "Press Enter"
    exit 1
}

$installationState = Join-Path $PSScriptRoot 'Runtime\installation_state.json'
$verifiedPython = ''
if (Test-Path -LiteralPath $installationState -PathType Leaf) {
    try {
        $state = Get-Content -LiteralPath $installationState -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($state.schema -eq 'bull-installation-state' -and $state.schema_version -eq 1 -and $state.status -eq 'complete') {
            $verifiedPython = [string]$state.python_executable
            if ($verifiedPython -and -not (Test-Path -LiteralPath $verifiedPython -PathType Leaf)) {
                throw 'Verified Python is missing. Run the BULL installer again.'
            }
        }
    } catch {
        Write-Host $_.Exception.Message -ForegroundColor Red
        Read-Host 'Enter = exit' | Out-Null
        exit 2
    }
}
if ($verifiedPython) {
    & $verifiedPython -u $client
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    & python -u $client
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 -u $client
} else {
    Write-Host "ERROR: Python not found in PATH." -ForegroundColor Red
    Read-Host "Press Enter"
    exit 1
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "Client exited with code $LASTEXITCODE" -ForegroundColor Red
    Write-Host "See client_debug.log in the client folder." -ForegroundColor Yellow
    Read-Host "Press Enter"
}
