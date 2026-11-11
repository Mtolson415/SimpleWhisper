$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$shortcutShell = New-Object -ComObject WScript.Shell
$desktopFolder = [Environment]::GetFolderPath('Desktop')
foreach ($shortcutInfo in @(
    @('Local Whisper Dictation', 'Start-Dictation.ps1'),
    @('Stop Whisper Dictation', 'Stop-Dictation.ps1')
)) {
    $shortcut = $shortcutShell.CreateShortcut((Join-Path $desktopFolder ($shortcutInfo[0] + '.lnk')))
    $shortcut.TargetPath = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
    $shortcut.Arguments = '-NoProfile -WindowStyle Hidden -File "' + (Join-Path $PSScriptRoot $shortcutInfo[1]) + '"'
    $shortcut.WorkingDirectory = $PSScriptRoot
    $shortcut.Description = 'Manage the local Whisper containers and portable companion.'
    $shortcut.Save()
}
# A user-session watcher is required for starts from Docker Desktop itself.
$portableExe = Join-Path $PSScriptRoot 'portable\LocalWhisperDictation\LocalWhisperDictation.exe'
if (!(Test-Path $portableExe)) { throw 'Build or extract the portable companion first.' }
$startupFolder = [Environment]::GetFolderPath('Startup')
$watcherShortcut = $shortcutShell.CreateShortcut((Join-Path $startupFolder 'Whisper Dictation Companion Watcher.lnk'))
$watcherShortcut.TargetPath = $portableExe
$watcherShortcut.Arguments = '--watch'
$watcherShortcut.WorkingDirectory = $PSScriptRoot
$watcherShortcut.Save()
Start-Process -FilePath $portableExe -ArgumentList '--watch' -WindowStyle Hidden
