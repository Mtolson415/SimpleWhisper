$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (!(Test-Path '.env')) { throw 'Copy .env.example to .env and set WHISPER_MODEL_DIR to your model directory.' }
py -3.14 -m venv .venv
if ($LASTEXITCODE -ne 0) { throw 'Python 3.14 is required.' }
& .venv\Scripts\python.exe -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
docker compose up -d --build
if ($LASTEXITCODE -ne 0) { throw 'Container build failed. Check Docker Desktop.' }
