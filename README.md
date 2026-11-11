# Local Whisper Dictation

[![Tests](https://github.com/Mtolson415/local-whisper-dictation/actions/workflows/test.yml/badge.svg)](https://github.com/Mtolson415/local-whisper-dictation/actions/workflows/test.yml)

Dictate into a Windows text field with **Ctrl+Alt+D**. Whisper inference runs inside Docker. A portable Windows companion handles the microphone, shortcut and pasting. Press once to record, speak, then press again to transcribe and paste. Review text before sending it.

This project does not require Lemonade, Open WebUI, a cloud speech account, or a language model to rewrite the transcript.

## Architecture

```text
Windows microphone → portable Windows companion → localhost Docker gateway
    → Whisper model in Docker → transcript → Windows clipboard → Ctrl+V
```

The WAV gateway and Whisper model runtime run in separate non-root containers. The portable companion runs on Windows because microphone and desktop input belong to that session. CPU inference is the portable baseline; GPU/NPU acceleration is not claimed.

## Requirements and setup

- Windows 11 x64 and Docker Desktop running Linux containers. Source development needs Python 3.14; the portable companion includes its own runtime.
- A model directory containing `ggml-base.bin`, `ggml-base.en.bin` and `ggml-large-v3-turbo.bin`. Copy `.env.example` to `.env` and set `WHISPER_MODEL_DIR` to its absolute path using forward slashes. Weights are external and excluded from Git and the portable ZIP.
- A working microphone enabled for desktop apps. Use the helper's microphone selector if the Windows default is wrong.

From PowerShell in this folder:

```powershell
.\Setup.ps1
.\Build-Portable.ps1
.\Install-Shortcuts.ps1
.\Start-Dictation.ps1
```

Setup installs pinned microphone dependencies and builds the gateway. Build-Portable produces an unsigned Windows x64 companion and a portable ZIP containing launcher/configuration files; models and `.env` are excluded. The portable bundle needs Docker Desktop and your model file, but no separate Python installation. If script policy blocks a script, use the individual commands in [the guide](docs/README.md) rather than changing security settings.

1. Open **Local Whisper Dictation** on the desktop. It starts Docker Desktop and both containers, waits for health checks, and enables the companion watcher.
2. Select your microphone in the helper, then click the intended text field in Word, an email draft, or another ordinary desktop application.
   Choose a model before recording: **Base** for English/Spanish, **Base.en** for English only, or **Large-v3 Turbo** for comparison with the larger multilingual model. One speech model is loaded at a time; all files are retained. The companion loads Base when opened. The selector also changes the shared Whisper service for other local applications using it.
   **Dictate directly into active input** is checked by default. Uncheck it to keep transcripts in the helper for review and manual copying; automatic pasting and clipboard changes are disabled in this mode.
3. Press **Ctrl+Alt+D**, speak, then press **Ctrl+Alt+D** again.
   For text during recording, enable **Live phrases — transcribe at short pauses** first. It updates at pauses or eight-second phrase boundaries; this is incremental phrase recognition, not word-by-word streaming. Base/Base.en are recommended.
4. Keep the same window active while transcription finishes. The helper requests a paste without pressing Enter.
5. If the active window changes, the transcript stays in the helper for manual copy/paste.

The per-user Windows watcher opens the companion when both containers start, including starts from Docker Desktop. Stopping/removing either container closes the companion; files and weights are retained. The watcher polls every two seconds and remains ready for a later start. Closing the companion yourself keeps it closed until the next stack start transition. Copy transcripts before stopping containers.

Install-Shortcuts adds desktop Start/Stop shortcuts and a **Whisper Dictation Companion Watcher** shortcut in your user Startup folder. Containers cannot directly open a Windows desktop application; this signed-in-session watcher supplies that connection. After moving the portable folder, rerun Install-Shortcuts. To disable automatic launch, remove that Startup shortcut and exit the watcher. **Stop Whisper Dictation** stops both services.

## Current verification — 2026-11-11

- Local Docker build/start and gateway health check passed.
- All 23 Windows tests passed. Containerized Linux checks pass 12 gateway/segmentation tests and skip 11 Windows-only checks.
- Synthetic five-second English/Spanish clips took 0.51–0.55 seconds with Base. An English selector test took 0.28 seconds with Base.en, 0.52 seconds with Base and 9.74 seconds with Turbo. All three model load/transcription checks passed. These are sample observations, not speed or accuracy guarantees.
- Windows microphone enumeration and default input format capability checks passed.
- Five Windows tests cover the direct-input checkbox, focus-change suppression, held-key delay, paste without Enter, and WAV encoding. These use fake desktop calls and do not prove real application insertion.
- Actual portable companion lifecycle checks passed for gateway stop/restart, removal/recreation and Whisper stop/restart. Paced synthetic live audio produced text before recording ended.
- **User microphone speech, actual paste into Word/email, reboot behavior, and a fully disconnected run remain pending.** Health reports the gateway process only, not model availability. This is an early working implementation, not a completed system-wide acceptance claim.

## Privacy and limits

Only loopback ports are published: gateway `17863` and Whisper `18081`. Requests go to the Whisper container, with no cloud fallback. Application code does not save recordings/transcripts to files. The upstream Whisper runtime may emit recognition details in container logs; treat them as private. The preview and Windows clipboard retain the latest transcript; clipboard history/sync are separate Windows settings. Other local processes can reach these unauthenticated loopback services. Do not expose them to a network.

Recording is limited to two minutes. Only mono 16-bit 16 kHz WAV is accepted. One model request runs at a time. Clipboard contents are replaced when pasting/copying; no previous clipboard contents are read. The guard checks the foreground **window**, not the exact field within it. Moving the cursor within the same window can change where text lands. Password fields and elevated applications are not supported targets. Recognition can make mistakes or hallucinate during silence; review every transcript.

## Learn, troubleshoot and recover

See [docs/README.md](docs/README.md) for choices, tests, dependencies/licenses, troubleshooting, recovery and verification boundaries. This repository contains source and synthetic tests only; models, personal recordings, transcripts and local environments are excluded.

The [repository map](docs/REPOSITORIES.md) identifies public/private ownership and cross-agent handoff rules. The [container AI integration summary](docs/AI-STACK.md) records the wider migration without exposing private deployment data.
