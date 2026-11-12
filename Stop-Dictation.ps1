$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
docker compose stop --timeout 10 dictation whisper
if ($LASTEXITCODE -ne 0) { throw 'Could not stop the dictation containers.' }
# The companion verifies both services are stopped and exits.
