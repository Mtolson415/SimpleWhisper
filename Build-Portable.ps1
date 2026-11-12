$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$portableDist = Join-Path $PSScriptRoot 'portable\v0.5.0'
& .venv\Scripts\python.exe -m pip install -r build-requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Build dependencies failed.' }
& .venv\Scripts\python.exe -m PyInstaller --noconfirm --windowed --onedir --name LocalWhisperDictation --distpath $portableDist --collect-all _sounddevice_data dictation.py
if ($LASTEXITCODE -ne 0) { throw 'Portable build failed.' }
$packageRoot = Join-Path $PSScriptRoot 'build\package-v0.5.0'
New-Item -ItemType Directory -Force "$packageRoot\portable\LocalWhisperDictation", "$packageRoot\docs" | Out-Null
Copy-Item "$portableDist\LocalWhisperDictation\*" "$packageRoot\portable\LocalWhisperDictation" -Recurse -Force
Copy-Item @('compose.yaml', 'Dockerfile', '.dockerignore', 'service.py', 'audio_segments.py', 'transcript_quality.py', 'windows_clipboard.py', 'windows_input.py', 'windows_focus.py', 'preferences.py', '.env.example', 'models.lock.json', 'Resolve-Companion.ps1', 'Start-Dictation.ps1', 'Stop-Dictation.ps1', 'Install-Shortcuts.ps1', 'README.md', 'LICENSE', 'AGENTS.md', 'CLAUDE.md', 'HANDOFF.md') $packageRoot -Force
Copy-Item docs\*.md "$packageRoot\docs" -Force
Compress-Archive -Path "$packageRoot\*" -DestinationPath LocalWhisperDictation-Windows-x64.zip -Force
