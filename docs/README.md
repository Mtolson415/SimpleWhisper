# Operating and learning guide - 0.5.3

The desktop shortcut now opens a matching dark startup checklist immediately. It checks app/configuration, starts Docker Desktop, waits separately for Whisper and the gateway to be healthy, then waits for a responding toolbar. A slim indeterminate progress animation and elapsed time indicate ongoing work without inventing a percentage. Successful startup dismisses the checklist; failure keeps diagnostic text visible and cleans up touched speech services. Repeated launches are serialized; an already-open app does not restart its services. The shortcut uses process-scoped RemoteSigned, with no permanent execution-policy change.

The microphone, On top switch and settings control use supersampled artwork with hover states. Microphone off/on uses muted rose/green; the independent pin switch uses slate/blue. Hit targets and focus routing are unchanged. Source PNG assets are included in portable builds and can be regenerated with `tools/Render-Controls.ps1`; no new runtime dependency is needed.

Recognition-generated `...` and Unicode ellipses are removed before desktop insertion, replacing mid-phrase ellipses with a space so words do not run together. Ordinary periods, decimals and other punctuation are retained. Ellipses intended as literal punctuation are also removed; this cleanup does not infer speaker intent. See the README's system requirements before first-time setup.

## Current choices

SimpleWhisper 0.5.2 uses the microphone as its listening button and the separate On top toggle for window pinning (on by default each launch). Both title bars and all settings/dropdown states use dark colors with light text. The desktop shortcut is now SimpleWhisper and keeps the feather icon. Internal service/repository and existing preference-folder names remain compatible.

In Settings, click Activation shortcut and press Ctrl or Alt plus A–Z, 0–9 or F1–F12; Shift is optional. Save registers the combination and persists it only on success. A conflict preserves the previous shortcut and displays an error. Global activation is suspended while Settings is open, so recording a binding cannot start the microphone. Microphone/model/shortcut preferences persist; the listening state does not.

The requested rollback removes the transcript-panel workflow and revision/background-lock machinery. The app is a dark always-on-top listening switch with a green/red microphone circle and a gear menu. It starts off and listens until explicitly turned off, without an automatic session timeout. Microphone, model and activation shortcut choices are available in Settings.

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

Build-Portable.ps1 builds portable/v0.5.3 and a ZIP using a fresh versioned staging directory. UI Automation/comtypes and the retired lock/revision modules are no longer runtime dependencies. Model weights and .env remain external. Install-Shortcuts creates one desktop launcher using the existing Tk feather resource from the bundled Tk DLL and removes this project's old resident Startup watcher. It removes only the legacy Stop desktop link that targets this project's stop script. After moving the portable folder, update .env and rerun shortcut installation.

Closing the app stops the microphone, cancels pending input and stops both project-owned speech containers (gateway and Whisper). The window reports Stopping dictation services until shutdown is verified. If cleanup cannot be confirmed, the visible app reports the error and allows closing again to retry rather than silently claiming success.

A wait-only lifetime helper watches the app's inherited process handle. It is active only while the app runs and exits after cleanup. If the app is forcibly terminated, the helper attempts the same scoped cleanup. There is no persistent sign-in/container watcher and no automatic reopening when containers start in Docker Desktop. The normal desktop shortcut starts both services and the app; launch failure also stops the owned services. Stop-Dictation.ps1 remains a recovery command, not a second desktop shortcut. Docker Desktop and unrelated containers are not stopped, and no model files, volumes or configuration are deleted.

LocalAppData/LocalWhisperDictation/settings.json stores only microphone/model/activation-shortcut choices. The listener always starts off. Removing that preferences file resets those choices; do not delete model files or private .env to reset the UI. Earlier source/portable versions remain recovery history, not the default launcher.

## Troubleshooting

The desktop launcher displays its checklist while Docker and both speech services prepare. A prior restart took about 30 seconds; cold Docker starts may take longer. If no checklist appears, reinstall the shortcut with `Install-Shortcuts.ps1` and check organization script policies. If a step fails, read the selectable details in the checklist. This application uses local Docker inference and has no Supabase dependency.

| Symptom | Check |
|---|---|
| No text in the destination | Verify green listening, the correct microphone and loaded model. Click the intended external field and read the short status message. |
| Old transcript-panel interface appears | Close older companions and launch the current desktop shortcut; the current title is SimpleWhisper. |
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

## Exit ownership and v1.0 gate

The latest direction requires no dictation-owned background processes after exit. Normal shutdown verifies both scoped containers are stopped; a process-handle supervisor covers abnormal owner termination and then exits. Only services with this project's Compose label and the allowlisted dictation/whisper service label are stopped. Other local AI containers and the shared Docker engine remain outside this app's ownership.

The simplified interface needs no feature expansion for v1.0. Actual packaged normal/forced-exit cleanup and close/reopen checks passed. The remaining release gate is real microphone-to-intended-application acceptance after the earlier input regressions, including a continuous listening/off/on trial. Record those results before calling v1.0 ready. General OS failure, a stopped Docker daemon or a forcibly killed cleanup helper cannot be guaranteed away; cleanup failures are not reported as success.

Packaged lifecycle acceptance uses DICTATION_LIFECYCLE_TEST=1 with unittest discover -s tests -p test_packaged_lifecycle.py. It starts the current package twice, opens no microphone, closes only its own window in the normal case and terminates only its own process in the forced case. Both cases verified no running dictation containers or project helper processes and preservation of unrelated container IDs. The inherited singleton guard and launcher wait also prevent a new owner from starting while prior cleanup is finishing. The installer removes the old resident Startup watcher; final installed state is closed with no dictation-owned services running.
