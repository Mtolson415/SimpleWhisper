# Local Whisper Dictation

Dictate into a Windows text field with **Ctrl+Alt+D**, using an existing local Whisper model. Press once to record, speak, then press again to transcribe and paste. Review the text before sending it.

This project separates desktop dictation from a chat application. It does not require Open WebUI, a cloud speech account, or a language model to rewrite the transcript.

## Architecture

```text
Windows microphone → Windows shortcut/helper → localhost Docker gateway
    → existing Lemonade Whisper → transcript → Windows clipboard → Ctrl+V
```

The WAV validation/API gateway runs in a non-root, read-only container. The microphone, hotkey and paste helper runs on Windows because those belong to the interactive desktop. **Whisper inference remains in the existing Windows Lemonade installation; the model runtime itself is not containerized by this project.**

## Requirements and setup

- Windows 11, Python 3.14 with Tk, Docker Desktop running Linux containers.
- An existing Lemonade server at port 13305 with `Whisper-Large-v3-Turbo` downloaded.
- A working microphone enabled for desktop apps. Use the helper's microphone selector if the Windows default is wrong.

From PowerShell in this folder:

```powershell
.\Setup.ps1
.\Start-Dictation.ps1
```

Setup installs pinned microphone dependencies into `.venv` and builds the gateway. Model download/configuration is an external prerequisite; setup does not download model weights. If local script policy blocks a script, use the individual commands in [the operating guide](docs/README.md) rather than changing security settings.

1. Leave Lemonade and Docker Desktop running. Start the helper once.
2. Select your microphone in the helper, then click the intended text field in Word, an email draft, or another ordinary desktop application.
3. Press **Ctrl+Alt+D**, speak, then press **Ctrl+Alt+D** again.
4. Keep the same window active while transcription finishes. The helper requests a paste without pressing Enter.
5. If the active window changes, the transcript stays in the helper for manual copy/paste.

Closing the helper stops microphone capture and releases the shortcut when its process exits. The small gateway can stay running; `docker compose stop` stops it.

## Current verification — 2026-11-11

- Local Docker build/start and gateway health check passed.
- Five containerized tests passed for valid PCM, wrong format, truncated audio, duration limits and prevention of invalid upstream requests.
- A synthetic English speech recording passed through this gateway and the installed Whisper model, returning the expected words and arithmetic question.
- Windows microphone enumeration and default input format capability checks passed.
- **User microphone speech, actual paste into Word/email, reboot behavior, and a fully disconnected run remain pending.** Health reports the gateway process only, not model availability. This is an early working implementation, not a completed system-wide acceptance claim.

## Privacy and limits

The service is bound to `127.0.0.1:17863`; requests are forwarded only to the fixed local Lemonade address. There is no cloud fallback. No recordings or transcripts are written to files or application logs. The most recent transcript remains visible in the helper and, after copy/paste, on the Windows clipboard; clipboard history/sync behavior is controlled by Windows. Other local processes can reach the unauthenticated loopback gateway. Do not expose it to a network.

Recording is limited to two minutes. Only mono 16-bit 16 kHz WAV is accepted. One model request runs at a time. Clipboard contents are replaced when pasting/copying; no previous clipboard contents are read. The guard checks the foreground **window**, not the exact field within it. Moving the cursor within the same window can change where text lands. Password fields and elevated applications are not supported targets. Recognition can make mistakes or hallucinate during silence; review every transcript.

## Learn, troubleshoot and recover

See [docs/README.md](docs/README.md) for choices, tests, dependencies/licenses, troubleshooting, recovery and verification boundaries. This repository contains source and synthetic tests only; models, personal recordings, transcripts and local environments are excluded.
