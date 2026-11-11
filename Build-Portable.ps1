$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$portableDist = Join-Path $PSScriptRoot 'portable\v0.4.0'
& .venv\Scripts\python.exe -m pip install -r build-requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Build dependencies failed.' }
& .venv\Scripts\python.exe -c "import comtypes.client; comtypes.client.GetModule('UIAutomationCore.dll')"
if ($LASTEXITCODE -ne 0) { throw 'Could not generate Windows accessibility interfaces.' }
& .venv\Scripts\python.exe -m PyInstaller --noconfirm --windowed --onedir --name LocalWhisperDictation --distpath $portableDist --collect-all _sounddevice_data --collect-all uiautomation --collect-submodules comtypes.gen dictation.py
if ($LASTEXITCODE -ne 0) { throw 'Portable build failed.' }
$packageRoot = Join-Path $PSScriptRoot 'build\package'
New-Item -ItemType Directory -Force "$packageRoot\portable\LocalWhisperDictation", "$packageRoot\docs" | Out-Null
Copy-Item "$portableDist\LocalWhisperDictation\*" "$packageRoot\portable\LocalWhisperDictation" -Recurse -Force
Copy-Item @('compose.yaml', 'Dockerfile', '.dockerignore', 'service.py', 'audio_segments.py', 'rolling_audio.py', 'transcript_quality.py', 'revision_span.py', 'windows_clipboard.py', 'windows_input.py', 'locked_target.py', '.env.example', 'models.lock.json', 'Resolve-Companion.ps1', 'Start-Dictation.ps1', 'Stop-Dictation.ps1', 'Install-Shortcuts.ps1', 'README.md', 'LICENSE', 'AGENTS.md', 'CLAUDE.md') $packageRoot -Force
Copy-Item docs\*.md "$packageRoot\docs" -Force
Compress-Archive -Path "$packageRoot\*" -DestinationPath LocalWhisperDictation-Windows-x64.zip -Force
