$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
& .venv\Scripts\python.exe -m pip install -r build-requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Build dependencies failed.' }
& .venv\Scripts\python.exe -m PyInstaller --noconfirm --windowed --onedir --name LocalWhisperDictation --distpath portable --collect-all _sounddevice_data dictation.py
if ($LASTEXITCODE -ne 0) { throw 'Portable build failed.' }
$packageRoot = Join-Path $PSScriptRoot 'build\package'
New-Item -ItemType Directory -Force "$packageRoot\portable\LocalWhisperDictation", "$packageRoot\docs" | Out-Null
Copy-Item 'portable\LocalWhisperDictation\*' "$packageRoot\portable\LocalWhisperDictation" -Recurse -Force
Copy-Item @('compose.yaml', 'Dockerfile', '.dockerignore', 'service.py', 'audio_segments.py', '.env.example', 'models.lock.json', 'Start-Dictation.ps1', 'Stop-Dictation.ps1', 'Install-Shortcuts.ps1', 'README.md', 'LICENSE') $packageRoot -Force
Copy-Item docs\README.md "$packageRoot\docs\README.md" -Force
Compress-Archive -Path "$packageRoot\*" -DestinationPath LocalWhisperDictation-Windows-x64.zip -Force
