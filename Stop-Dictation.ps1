$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
docker compose stop
if ($LASTEXITCODE -ne 0) { throw 'Could not stop the dictation containers.' }
# The companion notices the gateway stop and closes itself.
