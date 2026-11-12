# SimpleWhisper

[![Tests](https://github.com/Mtolson415/local-whisper-dictation/actions/workflows/test.yml/badge.svg)](https://github.com/Mtolson415/local-whisper-dictation/actions/workflows/test.yml)

A small, dark, always-on-top Windows dictation switch. Click the microphone or press your activation shortcut (default **Ctrl+Alt+D**), click your text field, and speak. A green circle behind the microphone means listening; red means off. Listening has **no automatic timeout**. Turn it off yourself.

Version **0.5.2** restores a simple direct-input workflow. No transcript panel, copy button, review-only mode, background field lock, rolling revisions or auto-stop selector remains. This deliberately supersedes the complex 0.3/0.4 interface. Earlier source and portable folders remain available for recovery.

## Use

The microphone starts/stops listening. The separate **On top** toggle controls whether the toolbar stays above other windows. Settings includes a shortcut field: click it, press Ctrl or Alt with a letter, number or F1–F12 (Shift optional), then Save. An unavailable shortcut keeps the previous binding. Shortcuts are suspended while Settings is open. The toolbar, title bars, dropdown fields and dropdown lists use a matching dark theme.

Startup recovery checked November 12: the installed launcher opened a responding window after about 30 seconds of speech-service preparation. See the operating guide for diagnosing a shortcut that appears inactive. This is a local Docker application with no Supabase dependency.

1. Open **SimpleWhisper** using the desktop shortcut. Docker Desktop and the speech containers must be running.
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

Build-Portable creates portable/v0.5.2 and a Windows ZIP. Models and private configuration are excluded. Install-Shortcuts updates the desktop launcher and removes the old resident Startup watcher. Exiting stops microphone capture, stops and verifies both dictation containers, and ends the app-lifetime helper. The desktop shortcut starts the services and opens the companion again. The executable is unsigned.

The desktop has one **SimpleWhisper** shortcut using the same Tk feather icon as the application. Closing the window stops microphone capture and both dictation speech services, so a separate Stop shortcut is unnecessary. Docker Desktop and unrelated containers are not stopped. Stop-Dictation.ps1 remains a recovery action; shortcut installation removes only the older Stop link owned by this project.

Only microphone/model/activation-shortcut choices persist in LocalAppData/LocalWhisperDictation/settings.json. Listening state and transcripts are never saved there. Re-select the microphone if Windows device names/indexes change.

## Verification - November 12, 2026

53 ordinary Windows checks passed, with two opt-in desktop/lifecycle checks skipped by default. That real owned two-window test also passed separately: an actual mouse click on the toolbar preserved external focus; Unicode was inserted; a stale result was rejected after switching windows; and fresh text reached the second destination. The test opened no microphone and targeted no user app. Containerized Linux passed 29 checks and skipped 26 Windows/interactive checks. The portable Windows build passed. Hosted results are checked separately.

Your microphone accuracy, actual intended-app acceptance, prolonged use, reboot/offline behavior and second-host recovery still need their own checks. Review dictated text in the destination before sending it.

## Privacy, learning and recovery

Only loopback ports 17863 and 18081 are published. Inference uses the fixed local Docker service without a cloud fallback. The application does not save speech recordings or transcript history. Internal clipboard transport replaces clipboard contents; there is no manual copy/paste workflow. Windows clipboard history/sync are separate system settings. Upstream Whisper logs can contain recognition text and should remain private.

See [the operating guide](docs/README.md), [primary-source implementation review](docs/IMPLEMENTATION-REVIEW.md), [repository map](docs/REPOSITORIES.md) and [current handoff](HANDOFF.md). The [design reference library](docs/DESIGN-REFERENCE-LIBRARY.md) remains reference documentation, not an asset database. Never commit recordings, transcripts, secrets, weights, private databases or backups.

## Exit ownership and v1.0 gate

The latest direction requires no dictation-owned background processes after exit. Normal shutdown verifies both scoped containers are stopped; a process-handle supervisor covers abnormal owner termination and then exits. Only services with this project's Compose label and the allowlisted dictation/whisper service label are stopped. Other local AI containers and the shared Docker engine remain outside this app's ownership.

The simplified interface needs no feature expansion for v1.0. Actual packaged normal/forced-exit cleanup and close/reopen checks passed. The remaining release gate is real microphone-to-intended-application acceptance after the earlier input regressions, including a continuous listening/off/on trial. Record those results before calling v1.0 ready. General OS failure, a stopped Docker daemon or a forcibly killed cleanup helper cannot be guaranteed away; cleanup failures are not reported as success.

Packaged lifecycle acceptance uses DICTATION_LIFECYCLE_TEST=1 with unittest discover -s tests -p test_packaged_lifecycle.py. It starts the current package twice, opens no microphone, closes only its own window in the normal case and terminates only its own process in the forced case. Both cases verified no running dictation containers or project helper processes and preservation of unrelated container IDs. The inherited singleton guard and launcher wait also prevent a new owner from starting while prior cleanup is finishing. The installer removes the old resident Startup watcher; final installed state is closed with no dictation-owned services running.
