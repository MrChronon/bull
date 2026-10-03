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

$expectedVersion = "v0.27.0.0"
$client = Join-Path $PSScriptRoot "bull_client_v0.27.0.0.py"
if (-not (Test-Path -LiteralPath $client)) { throw "Mandatory client missing: $client" }

$code = Get-Content -LiteralPath $client -Raw -Encoding UTF8
$m = [regex]::Match($code, 'APP_VERSION\s*=\s*[''"](?<v>v[^''"]+)[''"]')
if (-not $m.Success) { throw "APP_VERSION not found." }
$version = $m.Groups['v'].Value
if ($version -ne $expectedVersion) { throw "Unexpected APP_VERSION: $version" }

$required = @(
    "Docs\README.md",
    "Docs\USER_GUIDE.md",
    "Docs\UI_GUIDE.md",
    "Docs\USER_TESTS.md",
    "Docs\AI_CONTEXT.yaml",
    "Docs\PROMPTING_GUIDE.md",
    "Docs\BACKEND_SETUP.md",
    "Docs\REMOTE_ACCESS.md",
    "Docs\CODE_AUDIT.md",
    "Docs\SECURITY.md",
    "Docs\PUBLIC_RELEASE_CHECKLIST.md",
    "Docs\CHANGELOG_v0.27.0.0.md",
    "Docs\RELEASE_NOTES_0.27.0.0.md",
    "Docs\MIGRATION_TO_BULL.md",
    "README.md",
    "README_RU.md",
    "Docs\en\README.md",
    "Docs\en\USER_GUIDE.md",
    "Docs\en\BENCHMARKS.md",
    "Docs\en\CONNECTIONS.md",
    "Docs\en\SECURITY.md",
    "Docs\en\EXPERIMENTAL.md",
    "Docs\en\DEVELOPMENT.md",
    "Docs\en\RELEASE_NOTES.md",
    "Docs\ru\README.md",
    "Docs\ru\USER_GUIDE.md",
    "Docs\ru\BENCHMARKS.md",
    "Docs\ru\CONNECTIONS.md",
    "Docs\ru\SECURITY.md",
    "Docs\ru\EXPERIMENTAL.md",
    "Docs\ru\DEVELOPMENT.md",
    "Docs\ru\RELEASE_NOTES.md",
    ".gitignore",
    "CONTRIBUTING.md",
    ".github\SECURITY.md",
    ".github\ISSUE_TEMPLATE\bug_report.yml",
    ".github\ISSUE_TEMPLATE\feature_request.yml",
    ".github\ISSUE_TEMPLATE\config.yml",
    "Run-Tests.ps1",
    "Test-Public-Release.ps1",
    "Build-Release.ps1",
    "Tests\benchmark_regression.py",
    "Tests\agent_benchmark_regression.py",
    "Tests\hardening_regression.py",
    "Tests\ux_regression.py",
    "Tests\gpu_lab_regression.py",
    "Tests\bridge_regression.py",
    "Tests\core_regression.py",
    "Tests\registry_regression.py",
    "Tests\evidence_regression.py",
    "Tests\ru_dialogue_regression.py",
    "Tests\decision_support_regression.py",
    "Tests\user_tests_regression.py",
    "Tests\Build-Gpu-Lab-Fixture.ps1",
    "Server\Gpu-Lab-Worker.ps1",
    "Docs\GPU_LAB.md",
    "Shared\bull_llm\gpu_lab\__init__.py",
    "Shared\bull_llm\gpu_lab\contracts.py",
    "Shared\bull_llm\gpu_lab\transport.py",
    "Shared\bull_llm\gpu_lab\runner.py",
    "Shared\bull_llm\gpu_lab\reports.py",
    "Shared\bull_llm\gpu_lab\ui.py",
    "Shared\bull_llm\gpu_lab\messages.py",
    "Shared\bull_llm\terminal_ui.py",
    "Shared\bull_llm\connections_ui.py",
    "Shared\bull_llm\decision_support.py",
    "Shared\bull_llm\user_tests.py",
    "Shared\bull_llm\http_transport.py",
    "Shared\bull_llm\storage.py",
    "Shared\bull_llm\presentation.py",
    "Shared\bull_llm\i18n.py",
    "Docs\AUDIT_v0.27.0.0.md",
    "Docs\AGENT_BENCHMARK.md",
    "Apps\agent_benchmark_v0_27_0_0.py",
    "BULL-Agent-Lab-v0.27.0.0.cmd",
    "Schemas\agent_config_v1.schema.json",
    "Schemas\agent_run_v1.schema.json",
    "Shared\bull_llm\agent_benchmark\contracts.py",
    "Shared\bull_llm\agent_benchmark\runner.py",
    "Shared\bull_llm\agent_benchmark\tasks.py",
    "Shared\bull_llm\agent_benchmark\ollama.py",
    "Shared\bull_llm\agent_benchmark\telemetry.py",
    "Shared\bull_llm\agent_benchmark\reports.py",
    "Shared\bull_llm\agent_benchmark\ui.py",
    "Tests\Fixtures\ru_language_stress_sanitized_v2.json",
    "Tests\Fixtures\ru_language_stress_sanitized_v3.json",
    "Tests\Fixtures\benchmark_scorer_v3.json",
    "Apps\_bootstrap.py",
    "Apps\benchmark_lab_v0_27_0_0.py",
    "Apps\bull_client_app_v0_27_0_0.py",
    "Shared\bull_llm\__init__.py",
    "Shared\bull_llm\schemas.py",
    "Shared\bull_llm\profiles.py",
    "Shared\bull_llm\telemetry.py",
    "Shared\bull_llm\backends.py",
    "Shared\bull_llm\compatibility.py",
    "Shared\bull_llm\evidence.py",
    "Shared\bull_llm\core\__init__.py",
    "Shared\bull_llm\core\contracts.py",
    "Shared\bull_llm\core\fingerprints.py",
    "Shared\bull_llm\core\storage.py",
    "Shared\bull_llm\runtime\__init__.py",
    "Shared\bull_llm\runtime\adapters.py",
    "Shared\bull_llm\runtime\discovery.py",
    "Shared\bull_llm\runtime\events.py",
    "Shared\bull_llm\evaluation\__init__.py",
    "Shared\bull_llm\evaluation\service.py",
    "Shared\bull_llm\evaluation\registry.py",
    "Shared\bull_llm\reports.py",
    "backend_settings.json",
    "model_profiles.json",
    "benchmark_profiles.json",
    "BULL-v0.27.0.0.cmd",
    "BULL-Benchmark-Lab-v0.27.0.0.cmd",
    "BULL-v0.27.0.0.ps1",
    "BULL-v0.27.0.0.ico",
    "BULL-v0.27.0.0.png",
    "BULL-v0.27.0.0.svg",
    "Assets\Brand\bull-mark.svg",
    "Assets\Brand\bull-mark-light.svg",
    "Assets\Brand\bull-mark-mono.svg",
    "Assets\Brand\bull-wordmark.svg",
    "Assets\Brand\bull-logo-canonical.png",
    "Assets\Brand\bull-logo-canonical.svg",
    "Assets\Brand\bull-logo.png",
    "Assets\Brand\bull-wordmark.png",
    "Assets\Brand\bull-wordmark-red.png",
    "Assets\Brand\bull-wordmark-red.svg",
    "Assets\Brand\bull-mark.png",
    "Assets\Brand\bull-mark-red.png",
    "Assets\Brand\bull-mark-red.svg",
    "Assets\Brand\bull-mark-on-light.png",
    "Assets\Brand\bull-mark-on-dark.png",
    "Assets\Brand\bull-mark-mono.png",
    "Assets\Brand\brand-lock.json",
    "Assets\Brand\bull-mark-16.png",
    "Assets\Brand\bull-mark-24.png",
    "Assets\Brand\bull-mark-32.png",
    "Assets\Brand\bull-mark-48.png",
    "Assets\Brand\bull-mark-64.png",
    "Assets\Brand\bull-mark-128.png",
    "Assets\Brand\bull-mark-256.png",
    "Assets\Brand\bull-mark-512.png",
    "Assets\Brand\bull-mark-chafa-full-30.ansi.b64",
    "Assets\Localization\ui.en.json",
    "Assets\Brand\favicon.png",
    "Assets\Brand\github-social-preview.png",
    "Assets\Brand\README.md",
    "Tools\build_brand_assets.py",
    "Install-BULL-v0.27.0.0-Shortcut.ps1",
    "Install-BULL-v0.27.0.0.ps1",
    "Install-BULL-v0.27.0.0.cmd",
    "Server\Install-BULL-Node.ps1",
    "Server\Test-BULL-RemoteReadiness.ps1",
    "Server\connection.template.json",
    "Client\New-BULL-ClientKey.ps1",
    "BULL-v0.27.0.0-README.txt",
    "Schemas\bull_benchmark_pack_manifest_v1.schema.json",
    "Schemas\bull_benchmark_record_v1.schema.json",
    "Schemas\bull_benchmark_summary_v1.schema.json",
    "Docs\BENCHMARK_PACK_AUTHORING.md",
    "BenchmarkPacks\bull_chat_core\manifest.json",
    "BenchmarkPacks\bull_chat_core\cases.json",
    "BenchmarkPacks\bull_chat_core\gold.json",
    "BenchmarkPacks\bull_chat_core\pack.lock.json",
    "BenchmarkPacks\bull_chat_core\README.md",
    "BenchmarkPacks\bull_chat_core\LICENSE.txt",
    "Tools\build_chat_core_pack.py",
    "Tools\build_ru_dialogue_pack.py",
    "BenchmarkPacks\bull_ru_dialogue\manifest.json",
    "BenchmarkPacks\bull_ru_dialogue\cases.json",
    "BenchmarkPacks\bull_ru_dialogue\development_set.json",
    "BenchmarkPacks\bull_ru_dialogue\gold.json",
    "BenchmarkPacks\bull_ru_dialogue\scorer_gold.json",
    "BenchmarkPacks\bull_ru_dialogue\manual_audit.json",
    "BenchmarkPacks\bull_ru_dialogue\pack.lock.json",
    "BenchmarkPacks\bull_ru_dialogue\README.md",
    "BenchmarkPacks\bull_ru_dialogue\LICENSE.txt",
    "UserTests\README.md",
    "UserTests\simple_prompt.example.txt",
    "UserTests\structured_task.example.yaml"
)
foreach ($rel in $required) {
    if (-not (Test-Path -LiteralPath $rel)) {
        throw "Mandatory release file missing: $rel"
    }
}

$human = Get-Content -LiteralPath "Docs\USER_GUIDE.md" -Raw -Encoding UTF8
$ai = Get-Content -LiteralPath "Docs\AI_CONTEXT.yaml" -Raw -Encoding UTF8
if ($human -notmatch ('Версия клиента:\*{0,2}\s*' + [regex]::Escape($version))) {
    throw "USER_GUIDE client version mismatch."
}
if ($human -notmatch ('Версия документации:\*{0,2}\s*' + [regex]::Escape($version))) {
    throw "USER_GUIDE documentation version mismatch."
}
if ($ai -notmatch ('client_version:\s*["'']?' + [regex]::Escape($version) + '["'']?')) {
    throw "AI_CONTEXT client version mismatch."
}
if ($ai -notmatch ('documentation_version:\s*["'']?' + [regex]::Escape($version) + '["'']?')) {
    throw "AI_CONTEXT documentation version mismatch."
}
Write-Host "Documentation gate: OK" -ForegroundColor Green

$brandSvgs = @(
    'BULL-v0.27.0.0.svg',
    'Assets\Brand\bull-logo-canonical.svg',
    'Assets\Brand\bull-mark.svg',
    'Assets\Brand\bull-mark-light.svg',
    'Assets\Brand\bull-mark-mono.svg',
    'Assets\Brand\bull-wordmark.svg',
    'Assets\Brand\bull-wordmark-red.svg',
    'Assets\Brand\bull-mark-red.svg'
)
foreach ($svgPath in $brandSvgs) {
    [xml]$svg = Get-Content -LiteralPath $svgPath -Raw -Encoding UTF8
    $svgText = Get-Content -LiteralPath $svgPath -Raw -Encoding UTF8
    if ($svgText -match '<script|https?://(?!www\.w3\.org/2000/svg)') {
        throw "Unsafe external or executable content in brand asset: $svgPath"
    }
}
$brandLock = Get-Content -LiteralPath 'Assets\Brand\brand-lock.json' -Raw -Encoding UTF8 | ConvertFrom-Json
$canonicalLogo = 'Assets\Brand\bull-logo-canonical.png'
$canonicalHash = (Get-FileHash -LiteralPath $canonicalLogo -Algorithm SHA256).Hash.ToLowerInvariant()
if ($brandLock.schema -ne 'bull-brand-lock' -or $brandLock.schema_version -ne 1 -or
    $brandLock.derivation -ne 'crop_resize_only_no_redraw' -or
    $canonicalHash -ne '60d91a700b9cd91ad3fd6ad598287a8e2cccd067f2ab0ed7515dd52af44b2269' -or
    $canonicalHash -ne ([string]$brandLock.source_sha256).ToLowerInvariant()) {
    throw 'Canonical BULL logo or brand lock changed without approval.'
}
$iconBytes = [IO.File]::ReadAllBytes('BULL-v0.27.0.0.ico')
if ($iconBytes.Length -lt 6 -or $iconBytes[0] -ne 0 -or $iconBytes[1] -ne 0 -or
    $iconBytes[2] -ne 1 -or $iconBytes[3] -ne 0) {
    throw 'BULL Windows icon has an invalid ICO header.'
}
Write-Host 'Brand asset gate: OK' -ForegroundColor Green

# Public topology gate. A release always starts on local loopback and contains
# neither a personal endpoint nor a key path. Imported connections live under
# Runtime and are excluded below.
$publicSettings = Get-Content -LiteralPath 'backend_settings.json' -Raw -Encoding UTF8 | ConvertFrom-Json
if ($publicSettings.version -ne 3 -or $publicSettings.target_mode -ne 'local') {
    throw 'Public backend_settings.json must be schema v3 with target_mode=local.'
}
if ($publicSettings.remote_access.mode -ne 'manual' -or $publicSettings.remote_access.selected_connection_id) {
    throw 'Public backend settings must not auto-select a remote route or connection.'
}
foreach ($profile in $publicSettings.remote_access.profiles.PSObject.Properties.Value) {
    if ($profile.enabled -or $profile.host -or $profile.user -or $profile.identity_file) {
        throw 'Public backend settings contain a remote endpoint or identity path.'
    }
}
if ($publicSettings.ollama.transport -ne 'local' -or $publicSettings.ollama.auto_tunnel) {
    throw 'Public Ollama transport must be local with auto_tunnel=false.'
}
if ($publicSettings.llama_cpp.server_path -or $publicSettings.llama_cpp.models_dir) {
    throw 'Public llama.cpp settings contain a machine-specific path.'
}
Write-Host 'Public topology gate: OK' -ForegroundColor Green

# Windows PowerShell 5.1 treats BOM-less scripts as the active ANSI code page.
# A non-ASCII installer without BOM can parse differently after extraction and
# fail before it performs any action, so validate every shipped PowerShell file.
foreach ($scriptFile in Get-ChildItem -LiteralPath $PSScriptRoot -Recurse -File -Filter '*.ps1') {
    $scriptBytes = [IO.File]::ReadAllBytes($scriptFile.FullName)
    $hasUtf8Bom = $scriptBytes.Length -ge 3 -and $scriptBytes[0] -eq 0xEF -and
        $scriptBytes[1] -eq 0xBB -and $scriptBytes[2] -eq 0xBF
    if (-not $hasUtf8Bom -and @($scriptBytes | Where-Object { $_ -ge 128 }).Count) {
        throw "PowerShell 5.1 unsafe encoding (non-ASCII without BOM): $($scriptFile.FullName)"
    }
    $tokens = $null
    $parseErrors = $null
    [void][Management.Automation.Language.Parser]::ParseInput(
        [IO.File]::ReadAllText($scriptFile.FullName),
        [ref]$tokens,
        [ref]$parseErrors
    )
    if ($parseErrors.Count) {
        throw "PowerShell parse failure in $($scriptFile.FullName): $($parseErrors[0].Message)"
    }
}
Write-Host 'PowerShell 5.1 encoding + parse gate: OK' -ForegroundColor Green

Write-Host 'Running full public release privacy gate...' -ForegroundColor Cyan
& powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'Test-Public-Release.ps1') -Root $PSScriptRoot -AuditReleaseCandidatesOnly
if ($LASTEXITCODE -ne 0) { throw "Public release audit failed with code $LASTEXITCODE" }

# Exact obsolete-version gate.
$allowedVersioned = @(
    "bull_client_v0.27.0.0.py",
    "BULL-v0.27.0.0.cmd",
    "BULL-v0.27.0.0.ps1",
    "BULL-v0.27.0.0.ico",
    "BULL-v0.27.0.0.png",
    "BULL-v0.27.0.0.svg",
    "BULL-v0.27.0.0-README.txt",
    "Install-BULL-v0.27.0.0-Shortcut.ps1",
    "Install-BULL-v0.27.0.0.ps1",
    "Install-BULL-v0.27.0.0.cmd"
)
$obsolete = Get-ChildItem -LiteralPath . -File | Where-Object {
    ($_.Name -match '^(bull_client_v|BULL-v|Install-BULL-v)') -and
    ($allowedVersioned -notcontains $_.Name)
}
if ($obsolete) {
    throw "Obsolete versioned release artifacts found: $($obsolete.Name -join ', ')"
}

Write-Host "Running compile + offline regression gate..." -ForegroundColor Cyan
& powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'Run-Tests.ps1')
if ($LASTEXITCODE -ne 0) { throw "Regression gate failed with code $LASTEXITCODE" }

Write-Host "Running forced cp1251 regression gate..." -ForegroundColor Cyan
$oldUtf8=$env:PYTHONUTF8
$oldIo=$env:PYTHONIOENCODING
$oldPycachePrefix=$env:PYTHONPYCACHEPREFIX
$cp1251Pycache=Join-Path ([IO.Path]::GetTempPath()) ('bull-v02700-cp1251-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $cp1251Pycache -Force | Out-Null
try {
    $env:PYTHONUTF8='0'
    $env:PYTHONIOENCODING='cp1251'
    $env:PYTHONPYCACHEPREFIX=$cp1251Pycache
    if (Get-Command python -ErrorAction SilentlyContinue) {
        & python -u (Join-Path $PSScriptRoot 'Tests\benchmark_regression.py') | Out-Host
    } else {
        & py -3 -u (Join-Path $PSScriptRoot 'Tests\benchmark_regression.py') | Out-Host
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Forced cp1251 regression failed with code $LASTEXITCODE"
    }
} finally {
    $env:PYTHONUTF8=$oldUtf8
    $env:PYTHONIOENCODING=$oldIo
    $env:PYTHONPYCACHEPREFIX=$oldPycachePrefix
    $resolvedCp1251Pycache=[IO.Path]::GetFullPath($cp1251Pycache)
    $resolvedTempRoot=[IO.Path]::GetFullPath([IO.Path]::GetTempPath())
    if ($resolvedCp1251Pycache.StartsWith($resolvedTempRoot,[StringComparison]::OrdinalIgnoreCase) -and
        (Test-Path -LiteralPath $resolvedCp1251Pycache)) {
        Remove-Item -LiteralPath $resolvedCp1251Pycache -Recurse -Force
    }
}

$rootExcludedDirs = @('Chats','Benchmarks','Exports','Workspace','Runtime')
$anywhereExcludedDirs = @('__pycache__','.git','.codex','.agents','.venv','venv')
$excludedFilePatterns = @('*.llm-access*','connection*.private.json','*.pem','*.key','id_rsa','id_ed25519')

function Get-RelativePath([string]$fullPath) {
    return $fullPath.Substring($PWD.Path.Length + 1).Replace('\','/')
}
function Is-Excluded([string]$rel) {
    if ([System.IO.Path]::GetFileName($rel) -ieq 'client_debug.log') { return $true }
    if ([System.IO.Path]::GetFileName($rel) -ieq 'ui_settings.json') { return $true }
    $leaf=[System.IO.Path]::GetFileName($rel)
    foreach ($pattern in $excludedFilePatterns) {
        if ($leaf -like $pattern) { return $true }
    }
    $rootSegment = ($rel -split '/',2)[0]
    if ($rootExcludedDirs -icontains $rootSegment) { return $true }
    foreach ($d in $anywhereExcludedDirs) {
        if ($rel -match ('(^|/)' + [regex]::Escape($d) + '(/|$)')) { return $true }
    }
    return $false
}
function Get-ReleaseSourceFiles {
    return Get-ChildItem -LiteralPath . -Recurse -File -Force | Where-Object {
        $rel=Get-RelativePath $_.FullName
        (-not (Is-Excluded $rel)) -and
        ($_.Name -notlike '*.zip') -and
        ($_.Name -ne 'RELEASE_MANIFEST.json')
    }
}

$sourceCandidates = Get-ReleaseSourceFiles
$scannableTextExtensions = @('.py','.ps1','.cmd','.txt','.md','.yaml','.yml','.json','.toml','.ini','.cfg','.csv')
foreach ($file in $sourceCandidates) {
    if ($file.Length -gt 0 -and $file.Length -lt 8MB -and
        $scannableTextExtensions -contains $file.Extension.ToLowerInvariant()) {
        $raw = [IO.File]::ReadAllText($file.FullName)
        if ($raw -match '-----BEGIN (?:OPENSSH|RSA|EC|DSA) PRIVATE KEY-----') {
            throw "Private key material found in release source: $(Get-RelativePath $file.FullName)"
        }
    }
}
Write-Host 'Secrets/personal topology scan: OK' -ForegroundColor Green

Write-Host "Runtime/cache data: excluded without deleting source files" -ForegroundColor Green

# Build the manifest only after all source/docs changes are final.
$sourceFiles = Get-ReleaseSourceFiles
$manifest=[ordered]@{
    version=$version
    documentation_version=$version
    generated_at=(Get-Date).ToString('s')
    client_sha256=(Get-FileHash -LiteralPath $client -Algorithm SHA256).Hash.ToLower()
    validation=[ordered]@{
        documentation_gate='passed'
        python_compile='passed'
        ast_duplicate_functions='passed via regression'
        offline_regression='passed'
        forced_cp1251='passed'
        public_release_audit='passed'
        runtime_dirs_clean='passed'
        manifest_hash_verification='pending'
        zip_integrity='performed after manifest gate'
    }
    files=[ordered]@{}
}
foreach ($file in $sourceFiles) {
    $manifest.files[(Get-RelativePath $file.FullName)] =
        (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLower()
}
$manifest | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath 'RELEASE_MANIFEST.json' -Encoding UTF8

# Re-read the manifest and independently verify every listed file before packaging.
$verify = Get-Content -LiteralPath 'RELEASE_MANIFEST.json' -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($prop in $verify.files.PSObject.Properties) {
    $rel = $prop.Name
    $expected = [string]$prop.Value
    if (-not (Test-Path -LiteralPath $rel)) {
        throw "Manifest references missing file: $rel"
    }
    $actual = (Get-FileHash -LiteralPath $rel -Algorithm SHA256).Hash.ToLower()
    if ($actual -ne $expected) {
        throw "Manifest hash mismatch before packaging: $rel expected=$expected actual=$actual"
    }
}
Write-Host "Manifest hash verification: OK" -ForegroundColor Green
$manifest.validation.manifest_hash_verification='passed'
$manifest.validation.zip_integrity='verified by Build-Release.ps1 after archive creation'
$manifest | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath 'RELEASE_MANIFEST.json' -Encoding UTF8

$stage=Join-Path ([System.IO.Path]::GetTempPath()) ('BULL-'+[guid]::NewGuid().ToString('N'))
$bundleDir=Join-Path $stage "BULL-$version-Bundle"
New-Item -ItemType Directory -Path $bundleDir -Force | Out-Null

try {
    # Package the audited manifest set, not a fresh wildcard enumeration.
    $packageFiles = @($manifest.files.Keys | ForEach-Object { Get-Item -LiteralPath $_ })
    $packageFiles += Get-Item -LiteralPath 'RELEASE_MANIFEST.json'

    foreach ($file in $packageFiles) {
        $rel=Get-RelativePath $file.FullName
        $dest=Join-Path $bundleDir $rel
        $parent=Split-Path $dest -Parent
        if (-not (Test-Path -LiteralPath $parent)) {
            New-Item -ItemType Directory -Path $parent -Force | Out-Null
        }
        Copy-Item -LiteralPath $file.FullName -Destination $dest -Force
    }

    # Verify staged payload against the manifest too.
    $stagedManifest = Get-Content -LiteralPath (Join-Path $bundleDir 'RELEASE_MANIFEST.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    foreach ($prop in $stagedManifest.files.PSObject.Properties) {
        $rel = $prop.Name.Replace('/','\')
        $expected = [string]$prop.Value
        $staged = Join-Path $bundleDir $rel
        if (-not (Test-Path -LiteralPath $staged)) {
            throw "Staged manifest file missing: $rel"
        }
        $actual = (Get-FileHash -LiteralPath $staged -Algorithm SHA256).Hash.ToLower()
        if ($actual -ne $expected) {
            throw "Staged manifest hash mismatch: $rel"
        }
    }
    Write-Host "Staged payload hash verification: OK" -ForegroundColor Green

    & powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File (Join-Path $bundleDir 'Test-Public-Release.ps1') -Root $bundleDir
    if ($LASTEXITCODE -ne 0) { throw "Staged public release audit failed with code $LASTEXITCODE" }

    $zipName="BULL-$version-Bundle.zip"
    $zipPath=Join-Path (Split-Path $PSScriptRoot -Parent) $zipName
    if (Test-Path -LiteralPath $zipPath) {
        Remove-Item -LiteralPath $zipPath -Force
    }
    Add-Type -AssemblyName System.IO.Compression
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    # Windows PowerShell 5.1 Compress-Archive can emit backslash names. Write the
    # audited set explicitly with portable ZIP separators, including dotfiles.
    $writer=[System.IO.Compression.ZipFile]::Open($zipPath,[System.IO.Compression.ZipArchiveMode]::Create)
    try {
        $entryPaths=@($manifest.files.Keys) + @('RELEASE_MANIFEST.json')
        foreach ($entryPath in $entryPaths) {
            $entryName="BULL-$version-Bundle/" + $entryPath.Replace('\','/')
            $stagedPath=Join-Path $bundleDir $entryPath
            [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
                $writer,$stagedPath,$entryName,[System.IO.Compression.CompressionLevel]::Optimal
            ) | Out-Null
        }
    } finally { $writer.Dispose() }

    $z=[System.IO.Compression.ZipFile]::OpenRead($zipPath)
    try {
        if ($z.Entries.Count -lt 1) { throw 'ZIP is empty.' }
        foreach ($e in $z.Entries) {
            if (-not $e.FullName.StartsWith("BULL-$version-Bundle/")) {
                throw "ZIP has unexpected top-level entry: $($e.FullName)"
            }
            if ($e.FullName.EndsWith('/')) { continue }
            $relative = $e.FullName.Substring("BULL-$version-Bundle/".Length)
            $expectedHash = if ($relative -eq 'RELEASE_MANIFEST.json') {
                (Get-FileHash -LiteralPath 'RELEASE_MANIFEST.json' -Algorithm SHA256).Hash.ToLowerInvariant()
            } else { $manifest.files[$relative] }
            if (-not $expectedHash) { throw "ZIP contains unlisted file: $relative" }
            $entryStream = $e.Open()
            $hasher = [Security.Cryptography.SHA256]::Create()
            try { $actualHash = ([BitConverter]::ToString($hasher.ComputeHash($entryStream))).Replace('-','').ToLowerInvariant() }
            finally { $entryStream.Dispose(); $hasher.Dispose() }
            if ($actualHash -ne $expectedHash) { throw "ZIP content hash mismatch: $relative" }
        }
        $actualFiles = @($z.Entries | Where-Object { -not $_.FullName.EndsWith('/') })
        if ($actualFiles.Count -ne $manifest.files.Count + 1) { throw 'ZIP manifest file count mismatch.' }
    } finally {
        $z.Dispose()
    }

    $sha=(Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash.ToLower()
    $shaPath=$zipPath -replace '\.zip$','.sha256.txt'
    "$sha  $zipName" | Set-Content -LiteralPath $shaPath -Encoding ASCII

    Write-Host "ZIP integrity: OK" -ForegroundColor Green
    Write-Host "Release: $zipPath" -ForegroundColor Green
    Write-Host "SHA256:  $sha"
} finally {
    $resolvedStage=[IO.Path]::GetFullPath($stage)
    $releaseTempRoot=[IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\') + '\'
    if ($resolvedStage.StartsWith($releaseTempRoot,[StringComparison]::OrdinalIgnoreCase) -and
        ([IO.Path]::GetFileName($resolvedStage) -match '^BULL-[a-f0-9]{32}$')) {
        Remove-Item -LiteralPath $resolvedStage -Recurse -Force -ErrorAction SilentlyContinue
    }
}
