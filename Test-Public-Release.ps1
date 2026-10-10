param(
    [string]$Root = $PSScriptRoot,
    [string[]]$AdditionalPrivateMarkers = @(),
    [switch]$AuditReleaseCandidatesOnly
)

$ErrorActionPreference = 'Stop'
$rootPath = (Resolve-Path -LiteralPath $Root).Path
$failures = New-Object System.Collections.Generic.List[string]
$rootExcludedDirs = @('Chats','Benchmarks','Exports','Workspace','Runtime','Workspaces','PackExports','Installed','Trash')
$anywhereExcludedDirs = @('__pycache__','.git','.codex','.agents','.venv','venv')
$forbiddenNames = @(
    '.env','known_hosts','connections.json','client_debug.log','ui_settings.json',
    'id_rsa','id_ed25519','authorized_keys'
)
$forbiddenPatterns = @(
    '.env.*','*.pem','*.key','*.ppk','*.p12','*.pfx','*.pub','*.llm-access*',
    '*.private.json','*.connection.json'
)
$textExtensions = @('.py','.cs','.ps1','.cmd','.txt','.md','.yaml','.yml','.json','.toml','.ini','.cfg','.csv','.svg','.b64','.cff')

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
    if ($relative -eq 'Tests/Fixtures/bull_language_comparison@1.0.0.zip') {
        # Frozen, previously audited public base pack; cannot be silently replaced.
        if ((Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash -ne 'DB3A13A7E92B690B42866C7DD93E9400E7C6B4F020051352021BDE69E881A5E2') {
            Add-Finding 'Historical language fixture hash mismatch'
        }
        continue
    }
    if ($imageExtension -eq '.zip' -and $relative -match '^BasePacks/(?<pack>bull_chat_core|bull_extended_core|bull_ru_dialogue|bull_language_comparison)@1\.0\.[01]\.zip$') {
        # ZIPs cannot launder additional files past the source privacy audit.
        # Every entry must be byte-identical to an independently scanned source.
        $sourceDirectory=Join-Path $rootPath ('BenchmarkPacks/'+$Matches['pack'])
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        $archive=$null
        try {
            if ($file.Length -gt 8MB) { throw 'base archive too large' }
            $archive=[IO.Compression.ZipFile]::OpenRead($file.FullName)
            $entryNames=@()
            foreach ($entry in $archive.Entries) {
                if ($entry.FullName -notmatch '^[a-z0-9_.-]+$' -or $entry.Length -gt 8MB -or $entryNames -contains $entry.FullName) {
                    throw 'unsafe duplicate or oversized base ZIP entry'
                }
                $entryNames+=$entry.FullName
                $source=Join-Path $sourceDirectory $entry.FullName
                if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { throw 'extra ZIP entry' }
                $stream=$entry.Open()
                $hasher=[Security.Cryptography.SHA256]::Create()
                try { $hash=[BitConverter]::ToString($hasher.ComputeHash($stream)).Replace('-','') }
                finally { $stream.Dispose(); $hasher.Dispose() }
                if ($hash -ne (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash) { throw 'ZIP differs from audited source' }
            }
            $sourceFiles=@(Get-ChildItem -LiteralPath $sourceDirectory -File)
            if ($sourceFiles.Count -ne $entryNames.Count) { throw 'base ZIP missing source files' }
        } catch {
            Add-Finding "invalid or unaudited base archive: $relative ($($_.Exception.Message))"
        } finally { if ($archive) { $archive.Dispose() } }
        continue
    }
    if ($imageExtension -in @('.png','.ico')) {
        $approvedBrandImage = ($relative -match '^Assets/Brand/[a-z0-9._-]+\.png$') -or
            ($relative -in @('Assets/Brand/bull-icon-matrix.ico','Assets/Brand/bull-setup.ico')) -or
            ($file.Name -match '^BULL-v[0-9.]+\.(png|ico)$')
        if (-not $approvedBrandImage) {
            Add-Finding "unexpected binary image outside brand assets: $relative"
        }
        continue
    }
    if ($file.Extension -ieq '.exe' -or $relative -eq 'Setup/BULL.launcher.bin') {
        $approved = $relative -in @('Setup/BULL.launcher.bin','Setup.exe')
        $bytes = if ($file.Length -le 256KB) { [IO.File]::ReadAllBytes($file.FullName) } else { @() }
        $offset = if ($bytes.Length -ge 64) { [BitConverter]::ToInt32($bytes,60) } else { -1 }
        if (-not $approved -or $bytes.Length -lt 64 -or $bytes[0] -ne 77 -or $bytes[1] -ne 90 -or
            $offset -lt 64 -or $offset -gt ($bytes.Length - 4) -or
            [BitConverter]::ToUInt32($bytes,$offset) -ne 17744) {
            Add-Finding "unsupported or invalid native launcher: $relative"
        }
        continue
    }
    if ($file.Length -gt 8MB) {
        Add-Finding "oversized unaudited release file: $relative"
        continue
    }
    if ($textExtensions -notcontains $file.Extension.ToLowerInvariant() -and
        $file.Name -notin @('.gitignore','LICENSE') -and $relative -cne '.gitattributes') {
        Add-Finding "unsupported unaudited release file: $relative"
        continue
    }
    $raw = [IO.File]::ReadAllText($file.FullName)

    # Admit only the root byte-preservation policy; keep the full privacy scan.
    # Nested/custom Git attribute rules are not an arbitrary extension allowlist.
    if ($relative -ceq '.gitattributes') {
        $attributeRules = @($raw -split '\r?\n' | ForEach-Object { $_.Trim() } |
            Where-Object { $_ -and -not $_.StartsWith('#') })
        if ($attributeRules.Count -ne 1 -or $attributeRules[0] -cne '* -text') {
            Add-Finding 'unsupported Git byte-preservation policy'
        }
    }

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
        if ($email.Value -match '^(?:bull_chat_core|bull_extended_core|bull_ru_dialogue|bull_language_comparison)@1\.0\.[01]\.zip$') {
            continue # Exact base-pack filenames, not e-mail addresses.
        }
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
