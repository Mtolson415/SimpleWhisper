# Primary-source implementation review - November 12, 2026

The user requested checking research and code examples before finishing the simplified listener. This review uses primary Windows/library sources rather than an unreviewed third-party dictation script.

| Concern | Primary reference / official example | Application decision |
|---|---|---|
| Toolbar clicks steal the caret | [Extended window styles](https://learn.microsoft.com/en-us/windows/win32/winmsg/extended-window-styles) | Apply WS_EX_NOACTIVATE to the top-level toolbar. Exclude all companion-process windows as destinations. |
| Changed window style/topmost state | [SetWindowLongPtrW](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setwindowlongptrw), [SetWindowPos](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setwindowpos) | Use pointer-size-correct signatures and refresh the frame without activation. |
| Another application's focus | [GetFocus](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getfocus), [GetGUIThreadInfo](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getguithreadinfo), [GUITHREADINFO](https://learn.microsoft.com/en-us/windows/win32/api/winuser/ns-winuser-guithreadinfo) | Observe the foreground thread, initialize structure size, reject menu/drag/activation transitions and recheck foreground identity. No forced foreground handoff is used. |
| Keyboard input | [SendInput and its C++ example](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-sendinput) | Adapt the correctly sized input-array pattern to a checked Ctrl+V batch. Defer while modifiers are held and release keys after partial failure. Higher-privilege input limitations remain. |
| Microphone callback work | [sounddevice 0.5.6 callback rules](https://python-sounddevice.readthedocs.io/en/0.5.6/api/streams.html), [official examples](https://python-sounddevice.readthedocs.io/en/0.5.6/examples.html) | Copy/queue raw samples in the callback. Detect phrases and call the model in workers. Keep audio/work queues bounded and retain the default variable callback block size. |

## Changes resulting from review

- Added the frame-refresh flag after changing native window styles.
- Guarded native focus snapshots against menu/drag/activation transitions.
- Moved energy/phrase detection out of the stream callback.
- Kept one final-phrase input path instead of field rewrites and focus restoration.
- Tested a real mouse click without programmatically activating the toolbar first, which would invalidate the non-activation check.

The owned two-window desktop test passed toggle-click focus preservation, Unicode insertion, a destination switch, stale-result rejection and fresh insertion. That is evidence for those scenarios, not every application, exact identity of browser fields sharing a native window, microphone quality or uninterrupted hardware uptime. Python copy/queue operations are a practical implementation rather than a hard-real-time guarantee.

## Lifetime ownership follow-up

[Docker stop](https://docs.docker.com/reference/cli/docker/container/stop/) defines the grace period and eventual termination of selected container processes. Shutdown selects only the project label plus the dictation/whisper service allowlist and verifies the result. It never stops the shared Docker engine or unrelated projects.

The abnormal-exit helper follows Microsoft's [OpenProcess](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-openprocess) and [WaitForSingleObject](https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-waitforsingleobject) model. It receives an inherited wait-only process handle, avoiding PID-reuse races; it creates no UI/audio stream and exits after scoped cleanup. No resident watcher remains.
