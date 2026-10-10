param(
    [switch]$Quiet,
    [switch]$UpdateExistingOnly,
    [ValidateSet('bull_red','matrix_bright')][string]$Theme = 'bull_red',
    [string]$ShortcutStatePath = '',
    [string]$DesktopDirectory = '',
    [string]$ProgramsDirectory = ''
)
$ErrorActionPreference = "Stop"
$base = Split-Path -Parent $PSScriptRoot
$launcher = Join-Path $base 'BULL.exe'
$legacyLauncher = Join-Path $base 'BULL-v0.29.0.1.cmd'
$icon = if ($Theme -eq 'matrix_bright') { Join-Path $base 'Assets\Brand\bull-icon-matrix.ico' } else { Join-Path $base 'BULL-v0.29.0.1.ico' }
if (-not (Test-Path -LiteralPath $launcher)) { throw 'BULL.exe not found' }
if (-not (Test-Path -LiteralPath $icon)) { throw 'Theme icon not found' }
$statePath = if ($ShortcutStatePath) { $ShortcutStatePath } else { Join-Path $base 'Runtime\shortcut_state.json' }
if ($UpdateExistingOnly -and (Test-Path -LiteralPath $statePath)) {
    if ((Get-Item -LiteralPath $statePath).Length -gt 65536) { throw 'Invalid shortcut state' }
    $state = Get-Content -LiteralPath $statePath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($state.schema -eq 'bull-shortcut-state' -and $state.version -eq 1) {
        $DesktopDirectory = [string]$state.desktop
        $ProgramsDirectory = [string]$state.programs
    }
}
$ownedTargets = @([IO.Path]::GetFullPath($launcher), [IO.Path]::GetFullPath($legacyLauncher))
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class BullShortcutNotify {
    [DllImport("shell32.dll", CharSet=CharSet.Unicode)]
    public static extern void SHChangeNotify(uint eventId, uint flags, string item, IntPtr item2);
}
'@
$ws = New-Object -ComObject WScript.Shell
$desktopRoot = if ($DesktopDirectory) { $DesktopDirectory } else { [Environment]::GetFolderPath("Desktop") }
$programsRoot = if ($ProgramsDirectory) { $ProgramsDirectory } else { [Environment]::GetFolderPath("Programs") }
$targets = @(
    (Join-Path $desktopRoot "BULL.lnk"),
    (Join-Path $programsRoot "BULL.lnk")
)
foreach ($linkPath in $targets) {
    if ($UpdateExistingOnly) {
        if (-not (Test-Path -LiteralPath $linkPath)) { continue }
        $existing = $ws.CreateShortcut($linkPath)
        if (-not $existing.TargetPath -or -not $existing.WorkingDirectory) { continue }
        try {
            if ($ownedTargets -inotcontains [IO.Path]::GetFullPath($existing.TargetPath)) { continue }
            if ([IO.Path]::GetFullPath($existing.WorkingDirectory) -ine [IO.Path]::GetFullPath($base)) { continue }
        } catch { continue }
    }
    $parent = Split-Path -Parent $linkPath
    if (-not (Test-Path -LiteralPath $parent)) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
    $sc = $ws.CreateShortcut($linkPath)
    $sc.TargetPath = $launcher
    $sc.WorkingDirectory = $base
    $sc.IconLocation = "$icon,0"
    $sc.Description = "BULL v0.29.0.1 Benchmark Lab"
    $sc.Save()
    [BullShortcutNotify]::SHChangeNotify(0x00002000, 0x0005, $linkPath, [IntPtr]::Zero)
    if (-not $Quiet) { Write-Host "Shortcut created: $linkPath" -ForegroundColor Green }
}
if (-not $UpdateExistingOnly) {
    $parent = Split-Path -Parent $statePath
    if (-not (Test-Path -LiteralPath $parent)) { New-Item -ItemType Directory -Path $parent | Out-Null }
    $state = @{schema='bull-shortcut-state';version=1;desktop=$desktopRoot;programs=$programsRoot}
    $state | ConvertTo-Json | Set-Content -LiteralPath $statePath -Encoding UTF8
}
if (-not $Quiet) {
    Write-Host "Start BULL from the new Desktop or Start Menu shortcut." -ForegroundColor Cyan
}
