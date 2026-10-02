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
    $h = [Math]::Min(42, $max.Height)
    $buf = $raw.BufferSize
    if ($buf.Width -lt $w) { $buf.Width = $w }
    if ($buf.Height -lt 5000) { $buf.Height = 5000 }
    $raw.BufferSize = $buf
    $win = $raw.WindowSize
    $win.Width = $w
    $win.Height = $h
    $raw.WindowSize = $win
} catch {}

$client = Join-Path $PSScriptRoot "bull_client_v0.27.0.0.py"
if (-not (Test-Path $client)) {
    Write-Host "ERROR: bull_client_v0.27.0.0.py not found." -ForegroundColor Red
    Read-Host "Press Enter"
    exit 1
}

if (Get-Command python -ErrorAction SilentlyContinue) {
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
