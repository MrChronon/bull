[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$base = Split-Path -Parent $PSScriptRoot
$compiler = Join-Path ([Environment]::GetFolderPath('Windows')) 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
if (-not (Test-Path -LiteralPath $compiler)) { throw 'Windows .NET Framework C# compiler is required.' }
$source = Join-Path $PSScriptRoot 'BullLauncher.cs'
foreach ($role in @('client','setup')) {
    $name = if ($role -eq 'setup') { 'Setup.exe' } else { 'Setup\BULL.launcher.bin' }
    $iconName = if ($role -eq 'setup') { 'Assets\Brand\bull-setup.ico' } else { 'BULL-v0.29.0.1.ico' }
    $arguments = @('/nologo','/target:winexe','/platform:anycpu','/optimize+',
                   '/reference:System.Windows.Forms.dll',('/out:' + (Join-Path $base $name)),
                   ('/win32icon:' + (Join-Path $base $iconName)))
    if ($role -eq 'setup') { $arguments += '/define:SETUP' }
    & $compiler @arguments $source
    if ($LASTEXITCODE -ne 0) { throw "Launcher compilation failed: $name" }
    if ($role -eq 'setup') {
        & (Join-Path $base $name) --self-test
        if ($LASTEXITCODE -ne 0) { throw "Launcher companion files missing: $name" }
    }
    Write-Host "Portable launcher built: $name" -ForegroundColor Green
}
$legacyLauncher = [IO.Path]::GetFullPath((Join-Path $base 'BULL.exe'))
if ((Split-Path -Parent $legacyLauncher) -ne [IO.Path]::GetFullPath($base)) { throw 'Invalid legacy launcher target.' }
if (Test-Path -LiteralPath $legacyLauncher -PathType Leaf) { Remove-Item -LiteralPath $legacyLauncher }
