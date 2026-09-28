$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

try {
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [Console]::OutputEncoding = $utf8NoBom
    [Console]::InputEncoding = $utf8NoBom
    $OutputEncoding = $utf8NoBom
} catch {}

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:CUA_DD_PYTHON_TOOL_WARM_SPREADSHEET_RUNTIME = "0"
$env:CUA_DD_INIT_ARTIFACT_TOOL_V2_RECORD_OPERATIONS = "0"
$env:CUA_DD_INIT_ARTIFACT_TOOL_V2 = "0"

$client = Join-Path $PSScriptRoot "bull_client_v0.25.0.0.py"
$test = Join-Path $PSScriptRoot "Tests\benchmark_regression.py"

if (-not (Test-Path -LiteralPath $client)) { throw "Client file not found: $client" }
if (-not (Test-Path -LiteralPath $test)) { throw "Regression test file not found: $test" }

$python = $null
$pyArgs = @()
if (Get-Command python -ErrorAction SilentlyContinue) {
    $python = "python"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $python = "py"
    $pyArgs = @("-3")
} else {
    throw "Python not found in PATH."
}

$oldPycachePrefix = $env:PYTHONPYCACHEPREFIX
$testPycache = Join-Path ([IO.Path]::GetTempPath()) ('bull-v02500-pycache-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $testPycache -Force | Out-Null
$env:PYTHONPYCACHEPREFIX = $testPycache
try {
    Write-Host "Python compile..." -ForegroundColor Cyan
    & $python @pyArgs -m py_compile $client
    if ($LASTEXITCODE -ne 0) { throw "Python compile failed with code $LASTEXITCODE" }
    & $python @pyArgs -m compileall -q (Join-Path $PSScriptRoot 'Shared') (Join-Path $PSScriptRoot 'Apps')
    if ($LASTEXITCODE -ne 0) { throw "Module compile failed with code $LASTEXITCODE" }

    Write-Host "Offline regression..." -ForegroundColor Cyan
    & $python @pyArgs -u $test
    if ($LASTEXITCODE -ne 0) { throw "Regression tests failed with code $LASTEXITCODE" }
} finally {
    $env:PYTHONPYCACHEPREFIX = $oldPycachePrefix
    $resolvedPycache = [IO.Path]::GetFullPath($testPycache)
    $resolvedTemp = [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
    if ($resolvedPycache.StartsWith($resolvedTemp,[StringComparison]::OrdinalIgnoreCase) -and
        (Test-Path -LiteralPath $resolvedPycache)) {
        Remove-Item -LiteralPath $resolvedPycache -Recurse -Force
    }
}

Write-Host "Compile + regression tests: OK" -ForegroundColor Green
