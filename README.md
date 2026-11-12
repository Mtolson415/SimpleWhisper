# Local Whisper Dictation

[![Tests](https://github.com/Mtolson415/local-whisper-dictation/actions/workflows/test.yml/badge.svg)](https://github.com/Mtolson415/local-whisper-dictation/actions/workflows/test.yml)

A small, dark, always-on-top Windows dictation switch. Click the switch or press **Ctrl+Alt+D**, click your text field, and speak. A green circle behind the microphone means listening; red means off. Listening has **no automatic timeout**. Turn it off yourself.

Version **0.5.0** restores a simple direct-input workflow. No transcript panel, copy button, review-only mode, background field lock, rolling revisions or auto-stop selector remains. This deliberately supersedes the complex 0.3/0.4 interface. Earlier source and portable folders remain available for recovery.

## Use

1. Open **Local Whisper Dictation** using the desktop shortcut. Docker Desktop and the speech containers must be running.
2. With listening off, use the gear menu to select your microphone and model. **Base** is the fast English/Spanish default; **Base.en** is English only; **Turbo** is a slower multilingual comparison.
3. Click an external text field and switch listening on. Ordinary clicks on the floating switch are designed to leave the external caret in place.
4. Speak and pause briefly. Final phrases go directly into the active external field. No Enter is sent and no form is submitted.
5. Turn listening off yourself when finished. Already-recorded audio may finish recognition after stopping.

Opening the app never starts the microphone automatically. Green indicates capture enabled, not proof that recognition/input succeeded. The short status line reports problems. Every companion-process window, including its settings, is excluded as an input destination.

## Architecture and limits

```text
Windows microphone -> bounded frame queue -> phrase-detection worker
    -> localhost Docker gateway -> Whisper.cpp container
    -> internal Unicode clipboard + Ctrl+V -> active external field
```

The microphone callback only copies/queues samples. Detection, inference and desktop input run outside it. A phrase ends at roughly 0.6 seconds of quiet or eight seconds of speech. This is incremental phrase dictation, not word-by-word streaming. Individual requests/queues are bounded without a total listening-duration deadline.

The toolbar uses native non-activation styling. Foreground window and focused native child are checked before input. Stale results are discarded after a destination/session change; new speech is not permanently suppressed. Some apps share one native input window across several logical fields, so this does not identify every browser element. Keep focus stable while a phrase is being recognized if its destination matters. Elevated/password-field support, universal app compatibility and uninterrupted hardware uptime are not claimed.

## Setup and build

Requirements: Windows 11 x64, Docker Desktop with Linux containers, a microphone and external model files listed in models.lock.json. Source development uses Python 3.14; the portable companion includes its runtime.

```powershell
# Set WHISPER_MODEL_DIR in your private .env; see .env.example.
.\Setup.ps1
.\Build-Portable.ps1
.\Install-Shortcuts.ps1
.\Start-Dictation.ps1
```

Build-Portable creates portable/v0.5.0 and a Windows ZIP. Models and private configuration are excluded. Install-Shortcuts updates desktop and per-user Startup shortcuts. The signed-in-session watcher opens/closes the companion when both containers start/stop. Closing the companion stops capture; the desktop shortcut explicitly reopens it. The executable is unsigned.

Only microphone/model choices persist in LocalAppData/LocalWhisperDictation/settings.json. Listening state and transcripts are never saved there. Re-select the microphone if Windows device names/indexes change.

## Verification - November 12, 2026

41 ordinary Windows checks passed, with one interactive test skipped by default. That real owned two-window test also passed separately: an actual mouse click on the toolbar preserved external focus; Unicode was inserted; a stale result was rejected after switching windows; and fresh text reached the second destination. The test opened no microphone and targeted no user app. Containerized Linux passed 23 checks and skipped 19 Windows/interactive checks. The portable Windows build passed. Hosted results are checked separately.

Your microphone accuracy, actual intended-app acceptance, prolonged use, reboot/offline behavior and second-host recovery still need their own checks. Review dictated text in the destination before sending it.

## Privacy, learning and recovery

Only loopback ports 17863 and 18081 are published. Inference uses the fixed local Docker service without a cloud fallback. The application does not save speech recordings or transcript history. Internal clipboard transport replaces clipboard contents; there is no manual copy/paste workflow. Windows clipboard history/sync are separate system settings. Upstream Whisper logs can contain recognition text and should remain private.

See [the operating guide](docs/README.md), [primary-source implementation review](docs/IMPLEMENTATION-REVIEW.md), [repository map](docs/REPOSITORIES.md) and [current handoff](HANDOFF.md). The [design reference library](docs/DESIGN-REFERENCE-LIBRARY.md) remains reference documentation, not an asset database. Never commit recordings, transcripts, secrets, weights, private databases or backups.
