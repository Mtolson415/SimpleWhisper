param([hashtable]$State)
$ErrorActionPreference = 'Stop'
function Set-Stage([int]$Index, [string]$Message) {
    $State.Stage = $Index; $State.Message = $Message
}
function Invoke-DockerStep([string[]]$DockerArguments) {
    $ErrorActionPreference = 'Continue'
    $output = @(& docker @DockerArguments 2>&1)
    if ($LASTEXITCODE -ne 0) { throw (($output | Out-String).Trim()) }
}
$servicesTouched = $false
$owner = $null
$mutex = New-Object Threading.Mutex($false, 'Local\SimpleWhisper.Startup')
$locked = $false
try {
    $locked = $mutex.WaitOne(0)
    if (!$locked) { throw 'SimpleWhisper is already starting. Please wait for its other startup window.' }
    Set-Stage 0 'Checking the installed app and configuration...'
Set-Location $PSScriptRoot
. (Join-Path $PSScriptRoot 'Resolve-Companion.ps1')
$portableExe = Resolve-DictationCompanion
if (!$portableExe -and !(Test-Path '.venv\Scripts\pythonw.exe')) {
    throw 'Extract the portable companion or run Setup.ps1 first.'
}
if ($portableExe) {
    $dictationOwned = @(Get-CimInstance Win32_Process -Filter "Name='SimpleWhisper.exe'" | Where-Object { $_.ExecutablePath -eq $portableExe })
    if ($dictationOwned | Where-Object { $_.CommandLine -notmatch '--supervise-handle|--watch' }) {
        $State.Message = 'SimpleWhisper is already open. Look for the floating microphone toolbar.'
        $State.AlreadyOpen = $true; $State.Done = $true
        return
    }
    $dictationOwned | Where-Object { $_.CommandLine -match '--supervise-handle' } | ForEach-Object {
        Wait-Process -Id $_.ProcessId -Timeout 60 -ErrorAction SilentlyContinue
        if (Get-Process -Id $_.ProcessId -ErrorAction SilentlyContinue) { throw 'Previous dictation shutdown is still finishing.' }
    }
}
    if (!(Get-Command docker -ErrorAction SilentlyContinue)) { throw 'Install Docker Desktop with Linux containers, then try again.' }
    if (!(Test-Path '.env')) { throw 'Model configuration is missing. Complete the model-folder setup in the getting-started guide.' }
    Set-Stage 1 'Starting Docker Desktop. This may take a minute...'
    Invoke-DockerStep @('desktop', 'start', '--timeout', '90')
    Invoke-DockerStep @('info', '--format', '{{.ServerVersion}}')
    Set-Stage 2 'Loading the local speech model and checking its service...'
    $servicesTouched = $true
    Invoke-DockerStep @('compose', 'up', '-d', '--wait', '--wait-timeout', '180', 'whisper')
    Set-Stage 3 'Preparing the dictation connection...'
    Invoke-DockerStep @('compose', 'up', '-d', '--no-deps', '--wait', '--wait-timeout', '90', 'dictation')
    Set-Stage 4 'Opening the toolbar. Listening will start off.'
    if ($portableExe) {
        $owner = Start-Process -FilePath $portableExe -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -PassThru -ErrorAction Stop
    } else {
        $owner = Start-Process -FilePath "$PSScriptRoot\.venv\Scripts\pythonw.exe" -ArgumentList ('"' + "$PSScriptRoot\dictation.py" + '"') -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -PassThru -ErrorAction Stop
    }
    $deadline = [DateTime]::UtcNow.AddSeconds(30)
    do {
        Start-Sleep -Milliseconds 150
        $owner.Refresh()
        if ($owner.HasExited) { throw 'The app closed before its toolbar was ready. Check the app installation and try again.' }
        if ($owner.MainWindowHandle -ne 0 -and $owner.Responding) { break }
    } while ([DateTime]::UtcNow -lt $deadline)
    if ($owner.MainWindowHandle -eq 0 -or !$owner.Responding) { throw 'The toolbar did not become ready within 30 seconds. Try again.' }
    Set-Stage 5 'Choose a text field, then turn on the microphone.'
    $State.Done = $true
} catch {
    $State.Failed = $true; $State.Detail = $_.Exception.Message
    if ($owner -and !$owner.HasExited) { Stop-Process -Id $owner.Id -ErrorAction SilentlyContinue }
    if ($servicesTouched) {
        $State.Message = 'Cleaning up speech services...'
        try { Invoke-DockerStep @('compose', 'stop', '--timeout', '10', 'dictation', 'whisper') }
        catch { $State.Detail += "`n`nCleanup also needs attention: " + $_.Exception.Message }
    }
    $State.Message = 'Startup needs attention'; $State.Done = $true
} finally {
    if ($locked) { $mutex.ReleaseMutex() }
    $mutex.Dispose()
}
