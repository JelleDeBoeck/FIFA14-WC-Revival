$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$ConfigPath = Join-Path $ProjectRoot "config.local.psd1"

Write-Host "FIFA 14 WC Revival - Install Check"
Write-Host "----------------------------------"

if (-not (Test-Path $ConfigPath)) {
    throw "config.local.psd1 niet gevonden."
}

$config = Import-PowerShellDataFile $ConfigPath

if (-not (Test-Path $config.GameRoot)) {
    throw "GameRoot niet gevonden: $($config.GameRoot)"
}

if (-not (Test-Path $config.GameExe)) {
    throw "fifa14.exe niet gevonden: $($config.GameExe)"
}

$exe = Get-Item $config.GameExe

$ExpectedSha256 = "034991BCE371BB2D4E802184DC43E423B0FD7B6D06BF0E41EF12CA0DBC623916"
$ActualSha256 = (Get-FileHash $config.GameExe -Algorithm SHA256).Hash

if ($ActualSha256 -ne $ExpectedSha256) {
    throw "Onbekende fifa14.exe build. SHA256: $ActualSha256"
}

Write-Host "GameRoot : $($config.GameRoot)"
Write-Host "GameExe  : $($exe.FullName)"
Write-Host "EXE size : $($exe.Length) bytes"
Write-Host ""
Write-Host "[OK] FIFA 14 installatie gevonden."
Write-Host "SHA256   : $ActualSha256"
Write-Host "[OK] Ondersteunde FIFA 14 build."