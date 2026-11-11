$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (!(Test-Path '.venv\Scripts\pythonw.exe')) {
    throw 'Run Setup.ps1 first.'
}
docker compose up -d
if ($LASTEXITCODE -ne 0) { throw 'Start Docker Desktop and try again.' }
Start-Process -FilePath "$PSScriptRoot\.venv\Scripts\pythonw.exe" -ArgumentList ('"' + "$PSScriptRoot\dictation.py" + '"') -WorkingDirectory $PSScriptRoot -WindowStyle Hidden
