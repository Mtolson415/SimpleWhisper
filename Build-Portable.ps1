$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$portableDist = Join-Path $PSScriptRoot 'portable\v0.5.3'
& .venv\Scripts\python.exe -m pip install -r build-requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Build dependencies failed.' }
& .venv\Scripts\python.exe -m PyInstaller --noconfirm --windowed --onedir --name SimpleWhisper --distpath $portableDist --collect-all _sounddevice_data --add-data 'ui_assets;ui_assets' dictation.py
if ($LASTEXITCODE -ne 0) { throw 'Portable build failed.' }
$packageRoot = Join-Path $PSScriptRoot ('build\package-v0.5.3-' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force "$packageRoot\portable\SimpleWhisper", "$packageRoot\docs" | Out-Null
Copy-Item "$portableDist\SimpleWhisper\*" "$packageRoot\portable\SimpleWhisper" -Recurse -Force
Copy-Item @('compose.yaml', 'Dockerfile', '.dockerignore', 'service.py', 'audio_segments.py', 'transcript_quality.py', 'windows_clipboard.py', 'windows_input.py', 'windows_focus.py', 'preferences.py', 'lifecycle.py', '.env.example', 'models.lock.json', 'Resolve-Companion.ps1', 'Start-Dictation.ps1', 'Start-DictationWorker.ps1', 'Stop-Dictation.ps1', 'Install-Shortcuts.ps1', 'README.md', 'LICENSE', 'AGENTS.md', 'CLAUDE.md', 'HANDOFF.md') $packageRoot -Force
Copy-Item docs\*.md "$packageRoot\docs" -Force
Copy-Item docs\assets "$packageRoot\docs\assets" -Recurse -Force
Copy-Item ui_assets "$packageRoot\ui_assets" -Recurse -Force
Copy-Item @('CHANGELOG.md', 'CONTRIBUTING.md', 'CODE_OF_CONDUCT.md', 'SECURITY.md', 'THIRD_PARTY_NOTICES.md') $packageRoot -Force
$licenseRoot = Join-Path $packageRoot 'licenses'
New-Item -ItemType Directory -Force $licenseRoot | Out-Null
$pythonBase = & .venv\Scripts\python.exe -c 'import sys; print(sys.base_prefix)'
Copy-Item (Join-Path $pythonBase 'LICENSE.txt') (Join-Path $licenseRoot 'PYTHON-LICENSE.txt') -ErrorAction Stop
Get-ChildItem (Join-Path $pythonBase 'tcl') -Recurse -Filter 'license.terms' | ForEach-Object {
    $licenseName = $_.FullName.Substring($pythonBase.Length + 1).Replace('\', '-')
    Copy-Item $_.FullName (Join-Path $licenseRoot $licenseName) -ErrorAction Stop
}
@'
import importlib.metadata as md
from pathlib import Path
import shutil, sys
root = Path(sys.argv[1])
for name in ('sounddevice', 'cffi', 'pycparser', 'pyinstaller'):
    dist = md.distribution(name)
    for item in dist.files or ():
        if 'license' in str(item).lower() or 'copying' in item.name.lower():
            source = Path(dist.locate_file(item))
            if source.is_file():
                target = root / name / str(item).replace('../', '').replace('..\\', '')
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
'@ | & .venv\Scripts\python.exe - $licenseRoot
if ($LASTEXITCODE -ne 0) { throw 'Dependency license collection failed.' }
Compress-Archive -Path "$packageRoot\*" -DestinationPath SimpleWhisper-Windows-x64.zip -Force
