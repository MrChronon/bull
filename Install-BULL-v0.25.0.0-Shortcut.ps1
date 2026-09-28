param(
    [switch]$Quiet,
    [string]$DesktopDirectory = '',
    [string]$ProgramsDirectory = ''
)
$ErrorActionPreference = "Stop"
$base = $PSScriptRoot
$launcher = Join-Path $base "BULL-v0.25.0.0.cmd"
$icon = Join-Path $base "BULL-v0.25.0.0.ico"
if (-not (Test-Path $launcher)) { throw "BULL-v0.25.0.0.cmd not found in $base" }
if (-not (Test-Path $icon)) { throw "BULL-v0.25.0.0.ico not found in $base" }
$ws = New-Object -ComObject WScript.Shell
$desktopRoot = if ($DesktopDirectory) { $DesktopDirectory } else { [Environment]::GetFolderPath("Desktop") }
$programsRoot = if ($ProgramsDirectory) { $ProgramsDirectory } else { [Environment]::GetFolderPath("Programs") }
$targets = @(
    (Join-Path $desktopRoot "BULL.lnk"),
    (Join-Path $programsRoot "BULL.lnk")
)
foreach ($linkPath in $targets) {
    $parent = Split-Path -Parent $linkPath
    if (-not (Test-Path -LiteralPath $parent)) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
    $sc = $ws.CreateShortcut($linkPath)
    $sc.TargetPath = $launcher
    $sc.WorkingDirectory = $base
    $sc.IconLocation = "$icon,0"
    $sc.Description = "BULL v0.25.0.0 Benchmark Lab"
    $sc.Save()
    if (-not $Quiet) { Write-Host "Shortcut created: $linkPath" -ForegroundColor Green }
}
if (-not $Quiet) {
    Write-Host "Start BULL from the new Desktop or Start Menu shortcut." -ForegroundColor Cyan
}
