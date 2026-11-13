# Get started

[Project home](../README.md) · [Downloads](https://github.com/Mtolson415/local-whisper-dictation/releases) · [Troubleshooting](README.md#troubleshooting)

## Requirements

Windows 11 x64, microphone, Docker Desktop with Linux containers, and storage for images plus approximately 1.92 GB of models. CPU is the tested baseline. Python is needed only for source builds. Initial setup needs internet access.

## Install the portable release

1. Download `SimpleWhisper-Windows-x64.zip` and `SHA256SUMS.txt` from [0.5.2](https://github.com/Mtolson415/local-whisper-dictation/releases/tag/v0.5.2). Compare the ZIP hash:

   ```powershell
   Get-FileHash .\SimpleWhisper-Windows-x64.zip -Algorithm SHA256
   ```

2. Extract the whole ZIP to a writable folder. Keep scripts, Docker files, `docs` and `portable` together. The executable is unsigned; verify its origin.
3. Obtain all three models in [models.lock.json](../models.lock.json) from the [pinned upstream revision](https://huggingface.co/ggerganov/whisper.cpp/tree/5359861c739e955e79d9a303bcbc70fb988958b1). Store them together outside the app folder. Compare each SHA256 using `Get-FileHash`. The supplied Compose configuration expects all three files.
4. Copy `.env.example` to `.env` in the extracted folder. Set `WHISPER_MODEL_DIR` to your absolute model directory, for example `C:/Models/dictation`. Keep `.env` private.
5. Complete Docker Desktop's first-run setup once. Open PowerShell in the extracted folder and run `Start-Dictation.ps1`. Current source starts Docker Desktop automatically and shows a dark readiness checklist; initial image downloads take longer. Remove private paths/text before sharing errors.
6. Run `Install-Shortcuts.ps1` for a desktop shortcut with the existing feather icon. Rerun after moving the folder.

## First phrase

With listening off, select your microphone and **Base** in Settings. Click an ordinary scratch field, press **Ctrl+Alt+D**, speak, and pause. Review the result, then switch off. Closing stops owned speech services; Docker Desktop and unrelated containers remain running.

The microphone button toggles capture. **On top** controls pinning. Settings records Ctrl or Alt plus a letter, digit or F1–F12 (Shift optional). Shortcut conflicts preserve the previous binding. Opening never starts capture automatically.

## Build from source

Clone this repository; install Python 3.14 x64. Configure `.env` and models as above:

```powershell
.\Setup.ps1
.\Build-Portable.ps1
.\Install-Shortcuts.ps1
.\Start-Dictation.ps1
```

Output: `portable/v0.5.3/SimpleWhisper` and `SimpleWhisper-Windows-x64.zip`, excluding weights/private configuration. [System requirements](../README.md#system-requirements) · [Tests and contributions](../CONTRIBUTING.md).

## Update or remove

Close and wait for cleanup before updating. Extract each release into its own folder, configure `.env`, and reinstall the shortcut. Keep the old folder until verification. Preferences remain in `LocalAppData/LocalWhisperDictation/settings.json`.

To remove, close the app, remove its shortcut and extracted folder. External models, preferences and Docker images are separate. Do not delete shared Docker volumes. `Stop-Dictation.ps1` is a cleanup recovery command.
