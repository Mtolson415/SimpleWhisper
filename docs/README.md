# Operating and learning guide

## Why these choices

The existing Whisper file is mounted read-only into a pinned whisper.cpp CPU container, avoiding another model download. The gateway forwards WAV recordings to that container's `/inference` endpoint; Lemonade is not required. `sounddevice`/PortAudio captures microphone samples, Win32 RegisterHotKey registers one shortcut, and Tk supplies the companion UI. PyInstaller bundles the Windows runtime into a portable folder.

Alternatives: a browser recorder does not supply a global desktop shortcut; Windows voice typing uses another recognizer; a Linux desktop in a container is not the host Windows desktop. CPU inference is the portable baseline. GPU/NPU acceleration and equivalent performance to the old Windows runtime require separate verification.

## Manual setup and daily operation

```powershell
Copy-Item .env.example .env
# Set WHISPER_MODEL_DIR to your directory of speech model files.
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
docker compose up -d --build
.\.venv\Scripts\pythonw.exe dictation.py
```

Expected: both gateway and Whisper become healthy. Click a text field, press Ctrl+Alt+D, speak, press again, and keep the same window active. No form is submitted. Copy/paste manually if focus changed. Build-Portable.ps1 produces the portable companion and ZIP; Install-Shortcuts.ps1 installs desktop Start/Stop shortcuts and a user Startup watcher. The portable bundle requires Docker Desktop and the model file, but no separate Python installation. Keep the entire extracted folder together.

## Companion lifecycle and portable migration

The Windows watcher detects both dictation services using Docker project/service labels. Starting them from the desktop shortcut or Docker Desktop opens the companion. Stopping/removing either service closes it without deleting source, executables or weights. Copy transcripts before stopping. Closing the companion manually keeps it closed until a stack start transition. The watcher reconnects after Docker restarts; A confirmed container stop closes the companion. Transient Docker status failures are retried; three consecutive failures close it. It polls every two seconds in your signed-in session. Duplicate instances are prevented with per-session named mutexes. No Docker socket is mounted into containers.

Move the portable bundle and model file to the new machine, install Docker Desktop, update `.env`, rerun Install-Shortcuts.ps1, then start. For offline migration, export/load the pinned images first. Shortcuts contain local paths and must be recreated after moving the folder. The user Startup shortcut opens the watcher at sign-in. To disable it, remove only that shortcut and exit the watcher. The executable is unsigned; binary signing and second-host acceptance remain pending.

The **Dictate into active text box** checkbox starts checked to preserve the original behavior. Uncheck it for review-only dictation: transcripts still appear in the helper, but no clipboard change or automatic paste happens. The option is checked again before a delayed paste, so turning it off also cancels a paste waiting for shortcut keys to be released. This setting resets to checked when the helper restarts. The foreground-window guard remains active when the option is checked.

## Troubleshooting

| Symptom | Check and expected result |
|---|---|
| Shortcut is in use | Close another helper or application owning Ctrl+Alt+D; restart this helper. |
| No microphone / capture error | Select another input in the helper; verify it in Windows Sound settings yourself. No privacy settings are changed by this tool. |
| Transcription failed | Check both Docker services and WHISPER_MODEL_DIR. First model load can take longer than a warm request. |
| Companion missing or closes | Confirm the watcher is running and both containers are running. Check Docker CLI availability. |
| Text appears only in helper | A window switch intentionally suppresses paste; copy manually. Elevated apps may block input from a normal user process. |
| Wrong words or text during silence | Check mic selection, mute switch and ambient noise. Test a clear short phrase. Model accuracy is separate from transport success. |
| Gateway healthy but recognition fails | `/health` only verifies the gateway. A real WAV request is needed to verify Whisper. |

Diagnostic commands:

```powershell
docker compose ps
Invoke-RestMethod http://127.0.0.1:17863/health
.\.venv\Scripts\python.exe -m sounddevice
```

## Tests and acceptance

Run gateway tests in an isolated container:

```powershell
docker build -t local-whisper-dictation:0.1.0 .
docker run --rm --read-only --cap-drop ALL --security-opt no-new-privileges --mount "type=bind,source=$PWD\tests,target=/tests,readonly" local-whisper-dictation:0.1.0 python -B -m unittest discover -s /tests -v
```

Tests generate silent PCM samples in memory; no personal files or network/model services are required. CI repeats these tests and checks Python syntax. CI cannot prove Windows microphone access, recognition accuracy or insertion into a real application.

Additional mocked tests check container-stop events, Docker failures and requiring both model/gateway containers. Actual gateway stop closed the portable companion and a later start reopened it; tests do not establish reboot, second-host or real-application behavior.

Version 0.3.0 has 46 tests covering markers, segmentation, rolling queues, revision guards, gateway behavior and Windows controls. Linux skips Windows tests. Actual portable process checks also confirmed companion closure/reopening on gateway stop/restart, removal/recreation and model stop/restart. Paced synthetic live audio returned a phrase before recording ended. These do not prove actual microphone capture or Word/email input.

Manual acceptance: dictate “This is my local dictation test” into a scratch document; confirm start/stop status and actual words. Repeat with a window switch during recognition and confirm no automatic paste. Try the intended Word/email programs, then repeat with the network disconnected while local services remain running. Record results before claiming these checks passed. Do not use confidential material for a demonstration.

## Stop, recover, remove

Close the companion to stop capture. Stop-Dictation.ps1 or `docker compose stop` stops both services. `docker compose up -d --build` recreates the stateless services. Model weights are mounted read-only and remain unchanged. No named volumes, privileged mode or Docker socket access are used. Rebuild with Build-Portable.ps1 after source changes, closing existing companion/watcher processes before replacing executable files. Preserve the model, local `.env` and a known-good source/image set for recovery. No full second-host restore is claimed.

## Component and source record

| Component | Version / license | Primary source |
|---|---|---|
| Python container | 3.14.0-slim, digest pinned; Python PSF license, Debian component licenses | https://hub.docker.com/_/python |
| Windows Python tested | 3.14.7; PSF license | https://www.python.org/ |
| sounddevice | 0.5.6; MIT | https://github.com/spatialaudio/python-sounddevice |
| PortAudio bundled by Windows sounddevice wheel | Upstream PortAudio license; transitive native dependency | https://www.portaudio.com/license.html |
| CFFI | 2.1.1; MIT-0 | https://cffi.readthedocs.io/ |
| pycparser | 3.12; BSD-3-Clause | https://github.com/eliben/pycparser |
| Whisper.cpp | 1.9.5 build; pinned image digest in compose.yaml; MIT. Weights are external and not distributed | https://github.com/ggml-org/whisper.cpp |
| PyInstaller | 6.22.3; GPL-2.0-or-later with bootloader distribution exception | https://pyinstaller.org/en/stable/license.html |
| Win32 hotkey API | Windows system API | https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-registerhotkey |
| Desktop USB constraints | Docker Desktop documentation | https://docs.docker.com/desktop/troubleshoot-and-support/faqs/general/ |

The original application code is MIT licensed. Third-party software retains its own licenses. No model weights are included. Dependency vulnerability scanning, ARM portability, microphone signal quality and hardware acceleration performance have not been independently validated by this project.

## Speech models and live phrases

Put the three files listed in models.lock.json in WHISPER_MODEL_DIR. They come from a pinned upstream whisper.cpp model revision. Base.en is English only; Base and Large-v3 Turbo are multilingual, including English and Spanish. The selector loads one at a time through an allowlisted API; it never accepts an arbitrary model path. Files remain available. Opening the companion loads multilingual Base. The same Whisper container can serve the wider local assistant, so changing its model affects those requests too. Do not switch while another application is recording/transcribing.

Local five-second fixtures took about 0.5 seconds with Base and 0.28 seconds in an English Base.en check, versus about 10–12 seconds with Turbo. These do not establish accuracy for your microphone; the larger model is an optional comparison, not the routine dictation default. CPU-only contexts and load times differ from the old native runtime.

Enable **Live phrases — transcribe at short pauses** before recording for incremental dictation. The companion submits phrases after about 0.6 seconds of quiet, or after eight seconds of continuous speech, and appends results while recording continues. This is phrase-based incremental transcription, not native token-by-token streaming. The fixed energy threshold can miss quiet speech or treat noise as speech, and an eight-second boundary can cut a word. The bounded queue reports overload rather than storing unlimited audio; Base/Base.en are recommended. Leave it unchecked for the simpler stop-to-transcribe mode. Normal stop-to-transcribe recordings retain the two-minute limit. Continuous live sessions use the selected Auto-stop setting (Never by default).

In live mode only the new phrase is pasted; the preview retains the combined transcript. A window switch pauses ordinary live pasting; new phrases resume after returning to the original window. Phrases recognized away from that window stay only in preview. Held shortcut keys keep a phrase in preview rather than delaying a paste into a later recording. No Enter is sent. Always review text. Real microphone timing and application insertion remain user acceptance checks.

## Public/private coordination

Public reusable source and sanitized results live in this repository. The owner's paired private z13-ai-workspace-private repository holds deployment settings, handoffs and the public commit reference. AGENTS.md and CLAUDE.md tell each agent to pull current state, test and commit/push completed changes. Private details are represented here only by safe summaries. GitHub shares committed files, not chat history or model memory; each agent needs its own authorized access. Local GitHub Desktop synchronization can be once daily.


## Continuous mode, auto-stop and text quality (0.3.0)

Continuous listening and live mode start enabled. Microphone capture still starts only with Ctrl+Alt+D. Auto-stop offers Never, 2, 5, 15 or 30 minutes of recording duration. Choose settings before starting. Never removes the former two-minute live-session cap. Normal non-live capture remains bounded at two minutes, and every network request, work queue and preview remains bounded even in a long continuous session.

Microphone callback warnings do not end recording. A full phrase queue skips an older queued phrase and reports a warning while listening continues; use Base/Base.en to avoid falling behind. Confirmed container stops still close the companion. Three consecutive unknown Docker-status failures also close it; one-off failures no longer do so. Device disconnection, app/OS suspension and unavailable backend services cannot be guaranteed away by continuous mode.

The deterministic secondary check removes known bracketed recognition markers (including BLANK_AUDIO) and known Whisper control tokens. Checks run at the gateway, client decode and final insertion boundary. Ordinary bracketed content is preserved. This is not grammar correction or semantic proofreading. If a literal removed marker is needed, type it manually.

## Optional rolling drafts and post-insertion revisions

Enable Rolling drafts with revisions before starting. It submits growing, overlapping snapshots roughly once per second while speech continues; a pause or eight-second phrase boundary finalizes a span. Pending snapshots for the same phrase coalesce instead of accumulating. The recognition process runs in Docker, independently of the Windows UI. One fast loaded model is used; duplicated model instances are not required for this baseline. Base/Base.en are recommended.

Where a focused field supplies suitable Windows UI Automation text ranges, the companion can insert a provisional draft and revise only that inserted span. It checks field identity, caret position and the exact expected draft, and verifies the selected range before replacement. User edits, caret/focus changes, password fields and unsupported providers suppress revisions. There are no arbitrary Backspace sequences or whole-document rewrites. Unsupported fields retain rolling preview and receive final phrases using ordinary insertion. Compatibility is detected by the field's capabilities, not an application-name list; not every active text box is guaranteed to support revision.

The Windows clipboard path uses immediate Unicode data rather than Tk delayed rendering, which caused a native crash during UI Automation integration testing. UI Automation 2.0.29 and comtypes 1.5.0 are pinned (Apache-2.0 and MIT). The endpoint comparison uses the native COM range interface to avoid a wrapper defect in this pinned version. Primary API guidance: https://learn.microsoft.com/en-us/windows/win32/winauto/uiauto-usingtextrangeobjects and https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setclipboarddata .

Actual controlled WPF field tests verified initial insertion, replacement of only the draft, and preservation of surrounding synthetic text. A paced synthetic speech test produced its first rolling hypothesis before recording ended. These are narrower than live microphone acceptance in Word, browsers or desktop chat applications. Windows UI behavior, long-duration hardware stability, reboot/offline operation and second-host acceptance still need their own checks.

Builds go to a versioned portable folder so a new build can be prepared while the previous listener is open. The portable ZIP still uses the standard extracted folder layout. The desktop launcher explicitly opens the companion as well as its watcher, so manually closing the helper no longer requires a container restart to reopen it. Install-Shortcuts updates an old watcher without killing an active recorder; a listener restart activates the new executable.

## Design reference library

[The 87-site reference library](DESIGN-REFERENCE-LIBRARY.md) covers complete websites, app screens, components, themes, typography, icons, illustrations, motion, 3D models, templates, desktop toolkits and AI model catalogs. Start with a few clear visual references and preserve tested recording behavior during redesign.

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
