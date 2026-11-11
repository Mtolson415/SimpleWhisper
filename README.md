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
   **Dictate into active text box** is checked by default. Uncheck it to keep transcripts in the helper for review and manual copying; automatic pasting and clipboard changes are disabled in this mode.
3. Press **Ctrl+Alt+D**, speak, then press **Ctrl+Alt+D** again.
   For text during recording, enable **Live phrases — transcribe at short pauses** first. It updates at pauses or eight-second phrase boundaries; this is incremental phrase recognition, not word-by-word streaming. Base/Base.en are recommended.
4. With Lock to starting text box enabled, the helper captures the exact field at recording start. Compatible plain fields can keep receiving text after you click elsewhere. Other fields require the starting field to remain focused. No Enter is sent.
5. Turn Lock to starting text box off to follow the currently focused text box for each new phrase. Rolling revisions never follow a different field mid-phrase.

Version 0.3.0 adds **Continuous listening**, enabled with live mode by default. **Auto-stop** offers Never (default), 2, 5, 15 or 30 minutes of recording. Listening starts only when you press the shortcut. Never removes the old two-minute live-session cutoff while each audio request and the work queue remain bounded. Microphone warnings and one-off Docker status failures no longer immediately stop the listener.

The secondary quality check removes known markers such as `[BLANK_AUDIO]`, `[NO_SPEECH]` and Whisper control tokens before insertion. It does not use a language model to rewrite your meaning and preserves ordinary bracketed text.

Optional **Rolling drafts with revisions** starts recognition during speech, roughly once a second. In fields exposing verifiable Windows text ranges, it can replace only its last inserted draft after checking the caret, focus and exact text. Unsupported fields get rolling preview plus finalized phrase insertion. A detected manual edit or focus change stops automatic revisions. This is experimental capability-based support, not Apple-equivalent behavior in every application.

The per-user Windows watcher opens the companion when both containers start, including starts from Docker Desktop. Stopping/removing either container closes the companion; files and weights are retained. The watcher polls every two seconds and remains ready for a later start. Closing the companion yourself keeps it closed until the next stack start transition. Copy transcripts before stopping containers.

Install-Shortcuts adds desktop Start/Stop shortcuts and a **Whisper Dictation Companion Watcher** shortcut in your user Startup folder. Containers cannot directly open a Windows desktop application; this signed-in-session watcher supplies that connection. After moving the portable folder, rerun Install-Shortcuts. To disable automatic launch, remove that Startup shortcut and exit the watcher. **Stop Whisper Dictation** stops both services.

## Current verification — 2026-11-11

- Local Docker build/start and gateway health check passed.
- Version 0.4.0 has 69 checks: 67 pass in the ordinary Windows run and two interactive checks are opt-in. Linux passes 37 and skips 32 platform/interactive checks. The real two-field background insertion/revision check also passed locally; earlier results remain historical evidence.
- Synthetic five-second English/Spanish clips took 0.51–0.55 seconds with Base. An English selector test took 0.28 seconds with Base.en, 0.52 seconds with Base and 9.74 seconds with Turbo. All three model load/transcription checks passed. These are sample observations, not speed or accuracy guarantees.
- Windows microphone enumeration and default input format capability checks passed.
- Five Windows tests cover the direct-input checkbox, focus-change suppression, held-key delay, paste without Enter, and WAV encoding. These use fake desktop calls and do not prove real application insertion.
- Actual portable companion lifecycle checks passed for gateway stop/restart, removal/recreation and Whisper stop/restart. Paced synthetic live audio produced text before recording ended.
- **User microphone speech, actual paste into Word/email, reboot behavior, and a fully disconnected run remain pending.** Health reports the gateway process only, not model availability. This is an early working implementation, not a completed system-wide acceptance claim.

## Privacy and limits

Only loopback ports are published: gateway `17863` and Whisper `18081`. Requests go to the Whisper container, with no cloud fallback. Application code does not save recordings/transcripts to files. The upstream Whisper runtime may emit recognition details in container logs; treat them as private. The preview and Windows clipboard retain the latest transcript; clipboard history/sync are separate Windows settings. Other local processes can reach these unauthenticated loopback services. Do not expose them to a network.

Normal stop-to-transcribe recordings are limited to two minutes; continuous live sessions follow the selected auto-stop setting. Each WAV request is still bounded and one model request runs at a time. Copy/paste replaces clipboard contents without reading previous contents. Normal paste checks the foreground window; moving the cursor within it can change the destination. Rolling revisions additionally check an exact text range and caret. Password fields and elevated applications are unsupported. Recognition can make mistakes or hallucinate; review transcripts.

## Learn, troubleshoot and recover

See [docs/README.md](docs/README.md) for choices, tests, dependencies/licenses, troubleshooting, recovery and verification boundaries. This repository contains source and synthetic tests only; models, personal recordings, transcripts and local environments are excluded.

The [repository map](docs/REPOSITORIES.md) identifies public/private ownership and cross-agent handoff rules. The [container AI integration summary](docs/AI-STACK.md) records the wider migration without exposing private deployment data.

Browse the [87-site design and model reference library](docs/DESIGN-REFERENCE-LIBRARY.md) for website/app inspiration, components, themes, typography, icons, motion, templates, 3D assets and AI catalogs.

## Compact layout and paste repair (0.3.1)

The full Dictate into active text box label is visible. Labeled microphone/model selectors fill their rows, settings use two columns, and the transcript resizes with a scrollbar. A minimum window size keeps controls accessible.

Live phrases now wait for shortcut keys to be released instead of being discarded. Pending text is bounded to 20,000 characters and cancelled on destination change, disabling direct input, or starting a new recording. Native SendInput submits a checked Ctrl+V batch and reports blocked input; no Enter is sent. Elevated apps remain unsupported. After changing windows, restart recording in the intended text field or copy the preview manually.

Validation: 51 ordinary Windows tests passed; 28 containerized Linux tests passed with 24 platform/interactive skips. The additional opt-in synthetic scratch-field test passed real Unicode insertion and preserved existing text. Run with DICTATION_DESKTOP_TEST=1 and focus the test window within 20 seconds. It never opens the microphone. This does not establish microphone-to-app acceptance, every application's compatibility, reboot behavior or disconnected operation.

## Focus-guard correction (0.3.2)

User-reported failure: recognition reached the preview but status said Window changed. The older stop-to-transcribe default and the newer continuous-live default handled a window switch differently: live mode permanently latched paste suppression for that session. Version 0.3.2 pauses ordinary live insertion only while away from the original window, resumes new phrases upon return, and discards pending pastes on a switch rather than replaying them. Rolling draft revision stops remain strict because they protect previously inserted text. Starting a direct-input recording while the companion itself is focused now asks the user to click the intended destination first.

The native clipboard and checked paste batch are retained: the reported status shows paste was blocked before either was called. The earlier scratch-field success did not verify this focus-transition path or Codex compatibility. New regression tests exercise pause/return/resume, no insertion into a different window, and the companion-start guard. Codex microphone-to-chat acceptance remains user verification; do not describe it as passed.

## Destination lock and ordinary dictation (0.4.0)

**Dictate into active text box** controls whether any automatic input is allowed. **Lock to starting text box** starts checked and is fixed for a recording: click the intended field before Ctrl+Alt+D. Stop finishes already-recorded audio, then releases the destination. The next recording captures a new field. With lock off, finalized phrases follow the active window; the companion never pastes into its own preview automatically.

Compatible plain Edit fields exposing writable ValuePattern and an exact TextPattern selection/value mapping support locked background updates. Only that captured field is addressed; global Ctrl+V and the clipboard are not used for these writes. Original prefix/suffix are preserved, including when a selected span is replaced. The current value and control identity are checked before each update. A detected manual edit, disappearance, read-only change or rejected write stops automatic writes until a new recording. Field content exists only in memory and is bounded to 20,000 characters. Accessibility providers can briefly move focus during SetValue; the companion restores the previously focused control afterward. This is not a guarantee of imperceptible focus changes or atomicity against simultaneous typing.

Unsupported fields display Background lock unavailable and retain text in preview when the starting field is no longer focused. They never silently redirect a locked recording to another field. A whole rich document is not rewritten to simulate background insertion. Compatibility in Codex, browsers and Word remains unverified; the capability message describes the detected field rather than promising support for every app.

Rolling drafts remain experimental and off by default. Ordinary live phrases do not depend on the revision path. Compatible background locks can revise the last inserted draft using the same checked field state. Other rolling fields skip a phrase disrupted by a window switch and may resume later phrases; user edits still stop revisions. The previous permanent window-change latch has been removed for ordinary live dictation.

Validation: 67 ordinary Windows tests passed, two interactive tests skipped; Linux passed 37 with 32 skips. The opt-in two-field WPF test passed background Unicode insertion, last-draft revision, preservation of the other field and restoration of focus. Run it with DICTATION_DESKTOP_TEST=1 using unittest discover -s tests -p test_background_acceptance.py. The fixture contains synthetic text only and opens no microphone. These checks do not establish the user's microphone-to-application acceptance.
