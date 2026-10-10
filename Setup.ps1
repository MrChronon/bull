[CmdletBinding()]
param(
    [ValidateSet('en','ru')][string]$Language = '',
    [ValidateSet('bull_red','matrix_bright')][string]$Theme = '',
    [string]$PythonExecutable = '',
    [string]$ShortcutDesktop = '',
    [string]$ShortcutPrograms = '',
    [switch]$InstallDependencies
)

$ErrorActionPreference = 'Stop'
$utf8 = New-Object System.Text.UTF8Encoding($false)
try {
    [Console]::OutputEncoding = $utf8
    [Console]::InputEncoding = $utf8
    $OutputEncoding = $utf8
} catch {}
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

if (-not $Language) {
    Write-Host 'BULL - installation language / язык установки'
    Write-Host '  [1] English'
    Write-Host '  [2] Русский'
    while (-not $Language) {
        $choice = (Read-Host 'Language / Язык [1-2]').Trim().ToLowerInvariant()
        if ($choice -in @('1','en')) { $Language = 'en' }
        elseif ($choice -in @('2','ru')) { $Language = 'ru' }
    }
}

function Install-Text([string]$English,[string]$Russian) {
    if ($Language -eq 'ru') { return $Russian }
    return $English
}

if (-not $Theme) {
    Write-Host (Install-Text 'Choose the colour scheme' 'Выберите цветовую схему')
    Write-Host '  [1] BULL Red' -ForegroundColor Red
    Write-Host '  [2] BULL Matrix' -ForegroundColor Green
    while (-not $Theme) {
        $choice = (Read-Host (Install-Text 'Theme [1-2]' 'Тема [1-2]')).Trim().ToLowerInvariant()
        if ($choice -in @('1','red','bull red')) { $Theme = 'bull_red' }
        elseif ($choice -in @('2','matrix','bull matrix')) { $Theme = 'matrix_bright' }
    }
}
$setupAccent = if ($Theme -eq 'matrix_bright') { 'Green' } else { 'Red' }

function Find-Python {
    $candidates = @()
    if ($PythonExecutable) {
        $candidates += @{Exe=$PythonExecutable;Args=@()}
    } else {
        $localPython = Join-Path $PSScriptRoot 'Runtime\Python\Scripts\python.exe'
        if (Test-Path -LiteralPath $localPython -PathType Leaf) { $candidates += @{Exe=$localPython;Args=@()} }
        $py = Get-Command py.exe -ErrorAction SilentlyContinue
        if ($py) { $candidates += @{Exe=$py.Source;Args=@('-3')} }
        $python = Get-Command python.exe -ErrorAction SilentlyContinue
        if ($python) { $candidates += @{Exe=$python.Source;Args=@()} }
    }
    foreach ($candidate in $candidates) {
        try {
            $commandArgs = $candidate.Args
            $resolved = & $candidate.Exe @commandArgs -c 'import sys; print(sys.executable); sys.exit(0 if sys.version_info >= (3,10) else 1)' 2>$null
            $executable = [string](@($resolved)[-1])
            if ($LASTEXITCODE -eq 0 -and $executable -and (Test-Path -LiteralPath $executable -PathType Leaf)) {
                return $executable
            }
        } catch {}
    }
    return $null
}

try {
    Write-Host (Install-Text 'BULL Setup' 'Установка клиента BULL') -ForegroundColor $setupAccent
    $selectedPython = Find-Python
    if (-not $selectedPython) {
        Write-Host (Install-Text 'Python 3.10 or newer is required.' 'Нужен Python 3.10 или новее.') -ForegroundColor Yellow
        if (-not $InstallDependencies) {
            throw (Install-Text 'Install Python, then run setup again.' 'Установите Python и запустите установщик снова.')
        }
        $answer = Read-Host (Install-Text 'Install Python 3.12 with winget? [y/N]' 'Установить Python 3.12 через winget? [y/N]')
        if ($answer.Trim().ToLowerInvariant() -notin @('y','yes','да','д')) {
            throw (Install-Text 'Python installation was declined.' 'Установка Python отменена.')
        }
        $winget = Get-Command winget.exe -ErrorAction SilentlyContinue
        if (-not $winget) { throw (Install-Text 'winget is unavailable. Install Python manually.' 'winget недоступен. Установите Python вручную.') }
        & $winget.Source install --id Python.Python.3.12 --exact --accept-source-agreements --accept-package-agreements --silent --scope user
        if ($LASTEXITCODE -ne 0) { throw (Install-Text 'Python installation failed.' 'Не удалось установить Python.') }
        $env:PATH = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')
        $selectedPython = Find-Python
        if (-not $selectedPython) { throw (Install-Text 'Open a new terminal and run setup again.' 'Откройте новый терминал и запустите установщик снова.') }
    }
    $dependencyProbe = "import sys`ntry:`n import numpy, pandas, scipy, matplotlib`nexcept Exception:`n sys.exit(1)"
    & $selectedPython -I -c $dependencyProbe
    if ($LASTEXITCODE -ne 0) {
        Write-Host (Install-Text 'Full regression needs numpy, pandas, scipy and matplotlib. They are not models.' 'Для полной регрессии нужны numpy, pandas, scipy и matplotlib. Это не модели.') -ForegroundColor Yellow
        $answer = Read-Host (Install-Text 'Install verification libraries in Runtime/Python from PyPI? [y/N]' 'Установить библиотеки проверки из PyPI в Runtime/Python? [y/N]')
        if ($answer.Trim().ToLowerInvariant() -notin @('y','yes','да','д')) {
            throw (Install-Text 'Verification libraries are required for the full regression.' 'Библиотеки проверки необходимы для полной регрессии.')
        }
        $environmentDirectory = Join-Path $PSScriptRoot 'Runtime\Python'
        $environmentPython = Join-Path $environmentDirectory 'Scripts\python.exe'
        if (-not (Test-Path -LiteralPath $environmentPython -PathType Leaf)) {
            & $selectedPython -m venv $environmentDirectory
            if ($LASTEXITCODE -ne 0) { throw (Install-Text 'Cannot create the private Python environment.' 'Не удалось создать отдельное окружение Python.') }
        }
        $requirements = Join-Path $PSScriptRoot 'Setup\regression-requirements.txt'
        & $environmentPython -I -m pip --isolated install --index-url https://pypi.org/simple --only-binary=:all: --timeout 15 --retries 2 -r $requirements
        if ($LASTEXITCODE -ne 0) { throw (Install-Text 'Verification library installation failed. Retry setup.' 'Не удалось установить библиотеки проверки. Повторите установку.') }
        & $environmentPython -I -c 'import numpy, pandas, scipy, matplotlib'
        if ($LASTEXITCODE -ne 0) { throw (Install-Text 'Verification libraries are unavailable.' 'Библиотеки проверки недоступны.') }
        $selectedPython = $environmentPython
    }
    $wizard = Join-Path $PSScriptRoot 'Tools\install_bull.py'
    $wizardArgs = @($wizard,'--language',$Language,'--theme',$Theme)
    if ($ShortcutDesktop) { $wizardArgs += @('--desktop',$ShortcutDesktop) }
    if ($ShortcutPrograms) { $wizardArgs += @('--programs',$ShortcutPrograms) }
    & $selectedPython @wizardArgs
    exit $LASTEXITCODE
} catch {
    Write-Host (Install-Text 'Installation is not complete.' 'Установка не завершена.') -ForegroundColor Red
    Write-Host $_.Exception.Message
    Read-Host (Install-Text 'Enter = exit' 'Enter = выйти') | Out-Null
    exit 2
}
