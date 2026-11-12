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
$shortcut.Description = 'Open local dictation. Close the window to stop listening.'
$shortcut.IconLocation = $featherIcon
$shortcut.Save()
# Closing the app stops capture. Keep the backend-stop script as an optional
# maintenance action, without a second desktop shortcut. Remove only our link.
$legacyStopPath = Join-Path $desktopFolder 'Stop Whisper Dictation.lnk'
if (Test-Path -LiteralPath $legacyStopPath) {
    $legacyStop = $shortcutShell.CreateShortcut($legacyStopPath)
    $ownedStopScript = Join-Path $PSScriptRoot 'Stop-Dictation.ps1'
    if ($legacyStop.Arguments.IndexOf($ownedStopScript, [StringComparison]::OrdinalIgnoreCase) -ge 0) {
        Remove-Item -LiteralPath $legacyStopPath
    }
}
# A user-session watcher is required for starts from Docker Desktop itself.
$startupFolder = [Environment]::GetFolderPath('Startup')
$watcherShortcut = $shortcutShell.CreateShortcut((Join-Path $startupFolder 'Whisper Dictation Companion Watcher.lnk'))
$watcherShortcut.TargetPath = $portableExe
$watcherShortcut.Arguments = '--watch'
$watcherShortcut.WorkingDirectory = $PSScriptRoot
$watcherShortcut.IconLocation = $featherIcon
$watcherShortcut.Save()
# Replace only an old watcher in this project; leave an active recorder untouched.
$workspacePrefix = [IO.Path]::GetFullPath($PSScriptRoot).TrimEnd('\') + '\'
Get-CimInstance Win32_Process -Filter "Name='LocalWhisperDictation.exe'" | Where-Object {
    $_.ExecutablePath -and $_.ExecutablePath.StartsWith($workspacePrefix, [StringComparison]::OrdinalIgnoreCase) -and
    $_.ExecutablePath -ne $portableExe -and $_.CommandLine -match '--watch'
} | ForEach-Object { Stop-Process -Id $_.ProcessId }
Start-Process -FilePath $portableExe -ArgumentList '--watch' -WindowStyle Hidden
