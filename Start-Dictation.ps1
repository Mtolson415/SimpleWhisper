$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
. (Join-Path $PSScriptRoot 'Resolve-Companion.ps1')
$portableExe = Resolve-DictationCompanion
if (!$portableExe -and !(Test-Path '.venv\Scripts\pythonw.exe')) {
    throw 'Extract the portable companion or run Setup.ps1 first.'
}
docker desktop start --timeout 60
if ($LASTEXITCODE -ne 0) { throw 'Docker Desktop could not start.' }
docker compose up -d --wait --wait-timeout 180
if ($LASTEXITCODE -ne 0) { throw 'Start Docker Desktop and try again.' }
if ($portableExe) {
    Start-Process -FilePath $portableExe -ArgumentList '--watch' -WorkingDirectory $PSScriptRoot -WindowStyle Hidden
    Start-Process -FilePath $portableExe -WorkingDirectory $PSScriptRoot -WindowStyle Hidden
} else {
    Start-Process -FilePath "$PSScriptRoot\.venv\Scripts\pythonw.exe" -ArgumentList @(('"' + "$PSScriptRoot\dictation.py" + '"'), '--watch') -WorkingDirectory $PSScriptRoot -WindowStyle Hidden
    Start-Process -FilePath "$PSScriptRoot\.venv\Scripts\pythonw.exe" -ArgumentList ('"' + "$PSScriptRoot\dictation.py" + '"') -WorkingDirectory $PSScriptRoot -WindowStyle Hidden
}
