[CmdletBinding()]
param(
    [string]$Name = 'bull_access',
    [string]$KeyPath = '',
    [switch]$NoPassphrase,
    [switch]$NonInteractive
)

$ErrorActionPreference = 'Stop'
if ($Name -notmatch '^[A-Za-z0-9._-]{1,64}$') { throw 'Invalid key name.' }
$sshKeygen = Get-Command ssh-keygen.exe -ErrorAction SilentlyContinue
if (-not $sshKeygen) { throw 'OpenSSH Client / ssh-keygen is not installed.' }
$sshDir = Join-Path $env:USERPROFILE '.ssh'
New-Item -ItemType Directory -Path $sshDir -Force | Out-Null
$target = if ($KeyPath) { [IO.Path]::GetFullPath($KeyPath) } else { Join-Path $sshDir $Name }
if ((Test-Path -LiteralPath $target) -or (Test-Path -LiteralPath ($target+'.pub'))) {
    throw "Key already exists; it was not overwritten: $target"
}
if ($NonInteractive -and -not $NoPassphrase) {
    throw 'NonInteractive key generation requires explicit -NoPassphrase.'
}

$arguments = @('-t','ed25519','-a','100','-f',$target,'-C',"local-llm:$Name")
if ($NoPassphrase) { $arguments += @('-N','') }
& $sshKeygen.Source @arguments
if ($LASTEXITCODE -ne 0) { throw "ssh-keygen failed with exit $LASTEXITCODE" }

& icacls.exe $target /inheritance:r /grant:r "$($env:USERNAME):F" | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Failed to secure private key ACL.' }
Write-Host "Private key: $target" -ForegroundColor Green
Write-Host "Public key:  $target.pub" -ForegroundColor Cyan
Write-Warning 'Keep the private key secret. Send only the .pub file to the server administrator.'
