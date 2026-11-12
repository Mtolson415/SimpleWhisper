$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
. (Join-Path $PSScriptRoot 'Resolve-Companion.ps1')
$portableExe = Resolve-DictationCompanion
if (!$portableExe -and !(Test-Path '.venv\Scripts\pythonw.exe')) {
    throw 'Extract the portable companion or run Setup.ps1 first.'
}
if ($portableExe) {
    $dictationOwned = @(Get-CimInstance Win32_Process -Filter "Name='SimpleWhisper.exe'" | Where-Object { $_.ExecutablePath -eq $portableExe })
    if ($dictationOwned | Where-Object { $_.CommandLine -notmatch '--supervise-handle|--watch' }) {
        return # Already open; do not start another owner or restart its services.
    }
    $dictationOwned | Where-Object { $_.CommandLine -match '--supervise-handle' } | ForEach-Object {
        Wait-Process -Id $_.ProcessId -Timeout 60 -ErrorAction SilentlyContinue
        if (Get-Process -Id $_.ProcessId -ErrorAction SilentlyContinue) { throw 'Previous dictation shutdown is still finishing.' }
    }
}
try {
    docker desktop start --timeout 60
    if ($LASTEXITCODE -ne 0) { throw 'Docker Desktop could not start.' }
    docker compose up -d --wait --wait-timeout 180
    if ($LASTEXITCODE -ne 0) { throw 'Start Docker Desktop and try again.' }
    if ($portableExe) {
        Start-Process -FilePath $portableExe -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -ErrorAction Stop
    } else {
        Start-Process -FilePath "$PSScriptRoot\.venv\Scripts\pythonw.exe" -ArgumentList ('"' + "$PSScriptRoot\dictation.py" + '"') -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -ErrorAction Stop
    }
} catch {
    $dictationStartFailure = $_
    try { docker compose stop --timeout 10 dictation whisper | Out-Null } catch { }
    throw $dictationStartFailure
}
