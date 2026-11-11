# Operating and learning guide

## Why these choices

Reusing the installed Whisper model avoids a second model download and competing inference services. Lemonade exposes a documented audio transcription API. A small standard-library gateway validates WAV recordings without FFmpeg or third-party server dependencies. `sounddevice` uses PortAudio to capture microphone samples; Win32 `RegisterHotKey` registers one shortcut without a keyboard logging hook. Tk provides a visible status, microphone selector and transcript recovery box.

Alternatives: a browser recorder is useful for chat but does not supply a global desktop shortcut; Windows voice typing is a separate recognizer; an all-in-container Linux desktop would not be the host Windows desktop. Containerizing Whisper separately is a future portability option, with separate hardware/backend testing required. Docker Desktop device forwarding does not replace the interactive Windows helper.

## Manual setup and daily operation

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
docker compose up -d --build
.\.venv\Scripts\pythonw.exe dictation.py
```

Expected result: the helper opens with a microphone selector; the Docker gateway becomes healthy. Keep Lemonade running separately. Click an ordinary editable field, press Ctrl+Alt+D, speak, press again, then wait without changing windows. A transcript appears in the helper and a paste is requested in the active application. No form is submitted. Manual copy/paste is available if focus changed or paste is blocked.

## Troubleshooting

| Symptom | Check and expected result |
|---|---|
| Shortcut is in use | Close another helper or application owning Ctrl+Alt+D; restart this helper. |
| No microphone / capture error | Select another input in the helper; verify it in Windows Sound settings yourself. No privacy settings are changed by this tool. |
| Transcription failed | Check Lemonade is running and the model is installed; check Docker gateway health. First model load can take longer than a warm request. |
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

Manual acceptance: dictate “This is my local dictation test” into a scratch document; confirm start/stop status and actual words. Repeat with a window switch during recognition and confirm no automatic paste. Try the intended Word/email programs, then repeat with the network disconnected while local services remain running. Record results before claiming these checks passed. Do not use confidential material for a demonstration.

## Stop, recover, remove

Close the helper window to stop capture. `docker compose stop` stops only this project's gateway. `docker compose up -d --build` recreates the stateless gateway. If dependencies break, recreate only this repository's `.venv` and rerun setup. No persistent Docker volumes, model mounts, privileged containers or Docker socket access are used. The existing assistant and its volumes are not changed. Model/runtime recovery belongs to the Lemonade installation.

## Component and source record

| Component | Version / license | Primary source |
|---|---|---|
| Python container | 3.14.0-slim, digest pinned; Python PSF license, Debian component licenses | https://hub.docker.com/_/python |
| Windows Python tested | 3.14.7; PSF license | https://www.python.org/ |
| sounddevice | 0.5.6; MIT | https://github.com/spatialaudio/python-sounddevice |
| PortAudio bundled by Windows sounddevice wheel | Upstream PortAudio license; transitive native dependency | https://www.portaudio.com/license.html |
| CFFI | 2.1.1; MIT-0 | https://cffi.readthedocs.io/ |
| pycparser | 3.12; BSD-3-Clause | https://github.com/eliben/pycparser |
| External Lemonade / Whisper | Existing installation; not distributed or installed by this repository | https://github.com/lemonade-sdk/lemonade/blob/main/docs/api/openai.md |
| Win32 hotkey API | Windows system API | https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-registerhotkey |
| Desktop USB constraints | Docker Desktop documentation | https://docs.docker.com/desktop/troubleshoot-and-support/faqs/general/ |

The original application code is MIT licensed. Third-party software retains its own licenses. No model weights are included. Dependency vulnerability scanning, ARM portability, packaged executable distribution, microphone signal quality and hardware acceleration performance have not been independently validated by this project.
