# Operating and learning guide - 0.5.0

## Current choices

The requested rollback removes the transcript-panel workflow and revision/background-lock machinery. The app is a dark always-on-top listening switch with a green/red microphone circle and a gear menu. It starts off and listens until explicitly turned off, without an automatic session timeout. Microphone and model choices are the only settings.

Docker still owns Whisper inference; Windows owns the microphone, shortcut, floating UI and desktop input. Native non-activation styling keeps ordinary toolbar clicks from becoming the destination. All companion-process windows are excluded from input. Focus is observed without UI Automation, reading document contents or rewriting fields. Stale destination/session results are discarded without disabling future speech. Native handles cannot distinguish every logical field inside one browser/application window.

The bridge uses immediate Unicode clipboard data and a checked Ctrl+V batch, never Enter. Held modifiers/mouse buttons defer input. Phrase detection and model requests run in workers, outside the microphone callback. Audio frames, phrase jobs and pending input are bounded. Queue overflow warns instead of ending listening. This Python callback/queue implementation is not hard-real-time certification.

## Manual setup

```powershell
Copy-Item .env.example .env
# Set WHISPER_MODEL_DIR to the existing external speech-model directory.
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
docker compose up -d --build
.\.venv\Scripts\pythonw.exe dictation.py
```

Expected: a small red/off floating window. Use the gear menu while off to select a microphone/model. Click your external field and press Ctrl+Alt+D or click the switch. Green means capture enabled. Speech during settings focus is discarded; return to the external field to continue. No transcript editor or copy action exists.

Base supports English/Spanish and is the fast default. Base.en is English only. Turbo remains a slower optional CPU comparison, not a verified accuracy improvement for your microphone. One model is loaded at a time; selection affects the shared local Whisper service.

## Packaging, preferences and recovery

Build-Portable.ps1 builds portable/v0.5.0 and a ZIP using a fresh versioned staging directory. UI Automation/comtypes and the retired lock/revision modules are no longer runtime dependencies. Model weights and .env remain external. Install-Shortcuts creates one desktop launcher and updates the user Startup watcher, both using the existing Tk feather resource from the bundled Tk DLL. It removes only the legacy Stop desktop link that targets this project's stop script. After moving the portable folder, update .env and rerun shortcut installation.

The Windows watcher is required because a container cannot open a user's desktop app directly. Confirmed container stops close the companion. Three consecutive unknown Docker-status results also close it; isolated failures do not. Closing the companion stops capture. Start-Dictation explicitly reopens it. Nothing in this UI rollback deletes containers, model weights or configuration.

No separate desktop Stop shortcut is needed for normal use: close the app to stop listening. Containers remain running for reuse by this or other local tools. Stop-Dictation.ps1 is retained for optional backend shutdown. The shortcut icon reuses the existing feather resource rather than introducing a different microphone logo or a new image dependency.

LocalAppData/LocalWhisperDictation/settings.json stores only microphone/model choices. The listener always starts off. Removing that preferences file resets those choices; do not delete model files or private .env to reset the UI. Earlier source/portable versions remain recovery history, not the default launcher.

## Troubleshooting

| Symptom | Check |
|---|---|
| No text in the destination | Verify green listening, the correct microphone and loaded model. Click the intended external field and read the short status message. |
| Old transcript-panel interface appears | Close older companions and launch the current desktop shortcut; the current title is Whisper Dictation 0.5.0. |
| Destination changed | That delayed phrase was discarded. Keep focus steady for a phrase; new speech is allowed immediately. |
| Microphone unavailable | Turn listening off, select the intended device in settings, save and retry. Windows privacy settings are not changed. |
| Model/recognition unavailable | Check both Docker containers and the external model mount. Health alone does not prove model availability. |
| Input blocked | Protected/elevated apps may reject normal-process input. Test in an ordinary scratch field. The tool does not elevate itself or force focus. |
| Queue busy | Use Base/Base.en and a clearer pause. A phrase may be skipped; listening remains on. |
| Shortcut unavailable | Close an older listener or the application owning Ctrl+Alt+D. The visible switch remains usable. |

Known audio markers are removed without semantic rewriting. Recognition can still mishear or hallucinate; review the destination before sending. Internal clipboard writes overwrite its contents. OS clipboard history/sync are separate settings. Whisper logs may contain recognized speech and remain private.

## Tests and acceptance

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
docker build -t local-whisper-dictation:test .
docker run --rm --read-only --tmpfs /tmp:rw,noexec,nosuid,size=16m --cap-drop ALL --security-opt no-new-privileges --mount "type=bind,source=$PWD\tests,target=/tests,readonly" local-whisper-dictation:test python -B -m unittest discover -s /tests -v
```

For the opt-in desktop check, set DICTATION_DESKTOP_TEST=1 and run unittest discover -s tests -p test_desktop_acceptance.py. It creates its own synthetic external windows and a mocked-microphone toolbar. Focus the synthetic destination when requested; the test clicks its own toolbar. It verifies actual native focus preservation, Unicode insertion, stale-result rejection and fresh insertion after a destination switch. It never opens a microphone or targets a user app.

Other tests cover routing, own-process exclusion, stale sessions, held-key deferral, queue bounds, marker filtering, gateway validation, native input layout and preferences. Separate manual acceptance remains necessary for microphone quality, intended apps, long-running hardware, reboot, disconnected operation and a second host. Synthetic transport checks are not universal compatibility evidence.

## Dependencies and coordination

Windows Python 3.14.7 was tested; Dockerfile digest-pins Python 3.14.0-slim (Python PSF/Debian component licenses). Pinned dependencies: sounddevice 0.5.6 (MIT), CFFI 2.1.1 (MIT-0), pycparser 3.12 (BSD-3-Clause), PyInstaller 6.22.3 (GPL with bootloader exception). The sounddevice wheel bundles PortAudio under its upstream license. whisper.cpp 1.9.5 is image-digest pinned in compose.yaml (MIT); weights are external. Windows APIs are system components. The original source is MIT. No new package is required for the dark UI.

Read [the primary-source review](IMPLEMENTATION-REVIEW.md), [repository map](REPOSITORIES.md) and [handoff](../HANDOFF.md) before further work. Pull guidance, preserve user work, test and push completed milestones to the public/private pair. GitHub shares committed files, not chat history or model memory. Never commit recordings, transcripts, weights, private chat data, credentials or backups, even privately.
