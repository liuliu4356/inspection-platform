param(
    [ValidateSet("major", "minor", "patch")]
    [string]$Bump,
    [string]$Version
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

$repoRoot = Split-Path -Parent $PSScriptRoot
$versionFile = Join-Path $repoRoot "VERSION"
$pyprojectFile = Join-Path $repoRoot "backend\\pyproject.toml"

if (-not $Version -and -not $Bump) {
    throw "Provide -Version or -Bump."
}

$currentVersion = (Get-Content $versionFile -Raw).Trim()
$parts = $currentVersion.Split(".")
if ($parts.Count -ne 3) {
    throw "Current VERSION file is not valid semantic version: $currentVersion"
}

if (-not $Version) {
    $major = [int]$parts[0]
    $minor = [int]$parts[1]
    $patch = [int]$parts[2]

    switch ($Bump) {
        "major" { $major++; $minor = 0; $patch = 0 }
        "minor" { $minor++; $patch = 0 }
        "patch" { $patch++ }
    }

    $Version = "$major.$minor.$patch"
}

[System.IO.File]::WriteAllText($versionFile, "$Version`n", $utf8NoBom)

$pyproject = Get-Content $pyprojectFile -Raw
$updatedPyproject = [regex]::Replace(
    $pyproject,
    '(?m)^version = ".*"$',
    "version = ""$Version"""
)
[System.IO.File]::WriteAllText($pyprojectFile, $updatedPyproject, $utf8NoBom)
Write-Output "Version updated to $Version"
