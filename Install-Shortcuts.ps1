$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
. (Join-Path $PSScriptRoot 'Resolve-Companion.ps1')
$shortcutShell = New-Object -ComObject WScript.Shell
$desktopFolder = [Environment]::GetFolderPath('Desktop')
$portableExe = Resolve-DictationCompanion
if (!$portableExe) { throw 'Build or extract the portable companion first.' }
$tkIconLibrary = Get-ChildItem -LiteralPath (Join-Path (Split-Path $portableExe) '_internal') -Filter '*tk*.dll' | Select-Object -First 1
if (!$tkIconLibrary) { throw 'The companion Tk feather icon library is missing.' }
$featherIcon = $tkIconLibrary.FullName + ',0'
$shortcut = $shortcutShell.CreateShortcut((Join-Path $desktopFolder 'Local Whisper Dictation.lnk'))
$shortcut.TargetPath = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
$shortcut.Arguments = '-NoProfile -WindowStyle Hidden -File "' + (Join-Path $PSScriptRoot 'Start-Dictation.ps1') + '"'
$shortcut.WorkingDirectory = $PSScriptRoot
$shortcut.Description = 'Open local dictation. Exiting stops its microphone, speech services and helper.'
$shortcut.IconLocation = $featherIcon
$shortcut.Save()
# Closing the app stops capture and its services. Retain the recovery stop
# script without a second desktop shortcut. Remove only our legacy link.
$legacyStopPath = Join-Path $desktopFolder 'Stop Whisper Dictation.lnk'
if (Test-Path -LiteralPath $legacyStopPath) {
    $legacyStop = $shortcutShell.CreateShortcut($legacyStopPath)
    $ownedStopScript = Join-Path $PSScriptRoot 'Stop-Dictation.ps1'
    if ($legacyStop.Arguments.IndexOf($ownedStopScript, [StringComparison]::OrdinalIgnoreCase) -ge 0) {
        Remove-Item -LiteralPath $legacyStopPath
    }
}
# No resident sign-in watcher remains. The app's lifetime supervisor exits
# after cleanup. Remove only this project's old Startup shortcut/processes.
$workspacePrefix = [IO.Path]::GetFullPath($PSScriptRoot).TrimEnd('\') + '\'
$startupFolder = [Environment]::GetFolderPath('Startup')
$watcherShortcutPath = Join-Path $startupFolder 'Whisper Dictation Companion Watcher.lnk'
if (Test-Path -LiteralPath $watcherShortcutPath) {
    $oldWatcher = $shortcutShell.CreateShortcut($watcherShortcutPath)
    if ($oldWatcher.TargetPath.StartsWith($workspacePrefix, [StringComparison]::OrdinalIgnoreCase) -and $oldWatcher.Arguments -eq '--watch') {
        Remove-Item -LiteralPath $watcherShortcutPath
    }
}
Get-CimInstance Win32_Process -Filter "Name='LocalWhisperDictation.exe'" | Where-Object {
    $_.ExecutablePath -and $_.ExecutablePath.StartsWith($workspacePrefix, [StringComparison]::OrdinalIgnoreCase) -and
    $_.CommandLine -match '--watch'
} | ForEach-Object { Stop-Process -Id $_.ProcessId }
