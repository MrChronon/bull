param(
    [string]$Root = $PSScriptRoot,
    [string[]]$AdditionalPrivateMarkers = @(),
    [switch]$AuditReleaseCandidatesOnly
)

$ErrorActionPreference = 'Stop'
$rootPath = (Resolve-Path -LiteralPath $Root).Path
$failures = New-Object System.Collections.Generic.List[string]
$rootExcludedDirs = @('Chats','Benchmarks','Exports','Workspace','Runtime')
$anywhereExcludedDirs = @('__pycache__','.git','.codex','.agents','.venv','venv')
$forbiddenNames = @(
    '.env','known_hosts','connections.json','client_debug.log','ui_settings.json',
    'id_rsa','id_ed25519','authorized_keys'
)
$forbiddenPatterns = @(
    '.env.*','*.pem','*.key','*.ppk','*.p12','*.pfx','*.pub','*.llm-access*',
    '*.private.json','*.connection.json'
)
$textExtensions = @('.py','.ps1','.cmd','.txt','.md','.yaml','.yml','.json','.toml','.ini','.cfg','.csv','.svg','.b64')

function Add-Finding([string]$message) {
    $failures.Add($message)
}

function Relative-Path([string]$path) {
    return $path.Substring($rootPath.Length).TrimStart('\','/').Replace('\','/')
}

if (-not $AuditReleaseCandidatesOnly) {
    $directories = Get-ChildItem -LiteralPath $rootPath -Directory -Recurse -Force -ErrorAction SilentlyContinue
    foreach ($item in $directories) {
        $relative = Relative-Path $item.FullName
        $rootSegment = ($relative -split '/',2)[0]
        $isRootPrivate = ($rootExcludedDirs -icontains $rootSegment)
        $isCache = $false
        foreach ($directory in $anywhereExcludedDirs) {
            if ($relative -match ('(^|/)' + [regex]::Escape($directory) + '(/|$)')) {
                $isCache = $true
                break
            }
        }
        if ($isRootPrivate -or $isCache) {
            Add-Finding "runtime/development directory: $(Relative-Path $item.FullName)"
        }
    }
}

$files = Get-ChildItem -LiteralPath $rootPath -File -Recurse -Force
if ($AuditReleaseCandidatesOnly) {
    $files = @($files | Where-Object {
        $relative = Relative-Path $_.FullName
        $excluded = $false
        $rootSegment = ($relative -split '/',2)[0]
        if ($rootExcludedDirs -icontains $rootSegment) {
            $excluded = $true
        }
        foreach ($directory in $anywhereExcludedDirs) {
            if ($relative -match ('(^|/)' + [regex]::Escape($directory) + '(/|$)')) {
                $excluded = $true
                break
            }
        }
        if ($_.Name -ieq 'client_debug.log' -or $_.Name -ieq 'ui_settings.json') {
            $excluded = $true
        }
        -not $excluded
    })
}
foreach ($file in $files) {
    $relative = Relative-Path $file.FullName
    if ($forbiddenNames -icontains $file.Name) {
        Add-Finding "forbidden local file: $relative"
    }
    foreach ($pattern in $forbiddenPatterns) {
        if ($file.Name -like $pattern -and $file.Name -ine 'connection.template.json') {
            Add-Finding "credential-shaped file: $relative"
        }
    }
    if ($file.Name -match '(?i)^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}_.+\.(?:json|csv|html)$') {
        Add-Finding "raw benchmark artifact: $relative"
    }
    if ($file.Attributes -band [IO.FileAttributes]::ReparsePoint) {
        Add-Finding "release file is a link/reparse point: $relative"
        continue
    }
    $imageExtension = $file.Extension.ToLowerInvariant()
    if ($imageExtension -in @('.png','.ico')) {
        $approvedBrandImage = ($relative -match '^Assets/Brand/[a-z0-9._-]+\.png$') -or
            ($file.Name -match '^BULL-v[0-9.]+\.(png|ico)$')
        if (-not $approvedBrandImage) {
            Add-Finding "unexpected binary image outside brand assets: $relative"
        }
        continue
    }
    if ($file.Length -gt 8MB) {
        Add-Finding "oversized unaudited release file: $relative"
        continue
    }
    if ($textExtensions -notcontains $file.Extension.ToLowerInvariant() -and $file.Name -notin @('.gitignore','LICENSE')) {
        Add-Finding "unsupported unaudited release file: $relative"
        continue
    }
    $raw = [IO.File]::ReadAllText($file.FullName)

    # High-confidence credential formats. PRIVATE KEY markers are always forbidden.
    if ($raw -match '-----BEGIN (?:(?:OPENSSH|RSA|EC|DSA|ENCRYPTED) )?PRIVATE KEY-----') {
        Add-Finding "private key material: $relative"
    }
    foreach ($pattern in @(
        '\bgh[pousr]_[A-Za-z0-9]{28,}\b',
        '\bgithub_pat_[A-Za-z0-9_]{28,}\b',
        '\bhf_[A-Za-z0-9]{28,}\b',
        '\bsk-[A-Za-z0-9_-]{28,}\b',
        '\bAKIA[0-9A-Z]{16}\b',
        '\bAIza[0-9A-Za-z_-]{30,}\b'
    )) {
        if ($raw -match $pattern) { Add-Finding "credential token pattern: $relative" }
    }

    # High-risk example: C:\\Users\\<real-user>\\... . Placeholder users are allowed in tests/docs.
    $matches = [regex]::Matches($raw,'(?i)\b[A-Z]:[\\/]Users[\\/](?<user>[^\\/<>:"|?*\r\n]+)[\\/]')
    foreach ($match in $matches) {
        $user = $match.Groups['user'].Value
        if ($user -notin @('me','Public','Default','USERNAME','example','<user>')) {
            Add-Finding "personal Windows path ($user): $relative"
        }
    }
    $homeMatches = [regex]::Matches($raw,'(?i)(?:^|[\s"''])/home/(?<user>[a-z0-9._-]+)/')
    foreach ($match in $homeMatches) {
        if ($match.Groups['user'].Value -notin @('user','example','runner')) {
            Add-Finding "personal POSIX path: $relative"
        }
    }
    $emails = [regex]::Matches($raw,'(?i)\b[A-Z0-9._%+-]+@(?<domain>[A-Z0-9.-]+\.[A-Z]{2,})\b')
    foreach ($email in $emails) {
        if ($email.Groups['domain'].Value -notmatch '^(?:(?:[a-z0-9-]+\.)*example\.(?:com|org|net)|users\.noreply\.github\.com)$') {
            Add-Finding "non-example e-mail address: $relative"
        }
    }
    if ($AdditionalPrivateMarkers | Where-Object { $_ -and $raw.IndexOf($_,[StringComparison]::OrdinalIgnoreCase) -ge 0 }) {
        Add-Finding "additional private identity/topology marker: $relative"
    }
}

$settingsPath = Join-Path $rootPath 'backend_settings.json'
if (-not (Test-Path -LiteralPath $settingsPath)) {
    Add-Finding 'backend_settings.json missing'
} else {
    $settings = Get-Content -LiteralPath $settingsPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($settings.target_mode -ne 'local' -or $settings.remote_access.mode -ne 'manual' -or $settings.remote_access.selected_connection_id) {
        Add-Finding 'public backend settings select a remote target'
    }
    foreach ($profile in $settings.remote_access.profiles.PSObject.Properties.Value) {
        if ($profile.enabled -or $profile.host -or $profile.user -or $profile.identity_file) {
            Add-Finding 'public backend profile contains endpoint/identity data'
        }
    }
}

if ($failures.Count) {
    $failures | Sort-Object -Unique | ForEach-Object { Write-Host "FAIL  $_" -ForegroundColor Red }
    throw "Public release audit failed: $($failures.Count) finding(s)."
}

Write-Host "Public release audit: OK ($($files.Count) files scanned)" -ForegroundColor Green
