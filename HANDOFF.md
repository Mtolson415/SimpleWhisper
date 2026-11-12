# Current handoff - November 12, 2026

## SimpleWhisper 0.5.2

User-requested appearance/control update: renamed the application and desktop launcher to SimpleWhisper, matching dark toolbar/settings title bars and readable dark readonly/disabled comboboxes/popups. Microphone click controls listening; the former listening slider independently controls always on top. Settings records Ctrl/Alt plus letters, digits or F1–F12 (optional Shift), saves successful registrations, and preserves the active binding on conflict. Activation is suspended while Settings is open. Existing speech behavior, privacy boundaries and preference location are retained. The user previously reported the app working and complete; this is their subsequent requested revision.

Validation: 56 ordinary Windows checks passed (two opt-in checks skipped); the real owned two-window acceptance also passed with the microphone hit target, preserving external focus and Unicode insertion without opening a microphone. Visual preview verified dark title bars/fields/dropdown list, shortcut capture and independent pin-toggle rendering. Conflict-preservation and shortcut round-trip checks passed. The renamed portable SimpleWhisper.exe passed normal/forced-exit and reopen acceptance: both owned services/helpers stopped and unrelated containers were preserved. The desktop installer replaces only the owned old launcher with SimpleWhisper.lnk, retaining the feather icon. Final installed state is open with listening off. Hosted checks must be verified for this milestone.

## Startup investigation - November 12, 2026

Reported failure to open was not reproduced on the checked restart. Initially neither companion nor speech service was running. The installed launcher started both services, waited roughly 30 seconds for readiness, then opened a responding Whisper Dictation 0.5.1 window with its lifetime supervisor. Gateway health/models endpoints responded successfully. No microphone was opened and actual dictation remains unverified. The hidden launcher console makes preparation appear inactive; the operating guide now explains the wait and visible-console diagnostic. No runtime change was made. Supabase listed no accessible projects in the selected connection; this app has no Supabase dependency.

## 0.5.1 - simplified direct dictation

The latest user request supersedes the 0.3/0.4 direction: remove the app transcript/copy workflow, rolling revisions and background lock; provide a small dark always-on-top listener with one toggle, a green/red microphone indicator, a settings menu and no listening timeout.

Implemented one final-phrase path to the active external native destination. Ordinary clicks on the toolbar do not activate it. All companion-process windows are excluded as destinations. No transcript widget, copy action, field rewrite, UI Automation dependency, auto-stop selector or review-only toggle remains. Microphone/model choices persist locally; listening starts off. Settings are changed while off. Clipboard transport is internal.

The callback copies/queues raw frames; workers handle phrase detection and inference. Requests and queues are bounded without a total session deadline. Stale destination/session results are discarded without permanently disabling subsequent speech. Logical fields sharing a native input handle cannot always be distinguished.

The primary-source review is docs/IMPLEMENTATION-REVIEW.md. It led to a window-style refresh correction, focus-transition guards and moving phrase detection outside the callback.

53 ordinary Windows checks passed, with two opt-in desktop/lifecycle checks skipped. That owned two-window check also passed separately: real toggle-click focus preservation, Unicode input, stale-result rejection and fresh input in the second window. No microphone was opened and no user app was automated. Containerized Linux passed 29 checks and skipped 26 Windows/interactive checks. The portable Windows build passed. Preference tests use a small isolated /tmp tmpfs while the rest of the test container remains read-only. Hosted results must be checked separately after pushing.

Microphone quality, actual intended-app acceptance, prolonged hardware stability, reboot/offline and second-host recovery remain unverified. Do not describe synthetic transport checks as universal dictation acceptance.

Public/private ownership remains docs/REPOSITORIES.md. The launcher should resolve portable/v0.5.1. Earlier source/portable versions remain recovery history. Never commit local settings, recordings, transcripts, raw conversations, credentials, weights or backups. Pull shared guidance before subsequent work.

Desktop shortcut follow-up: the user explicitly selected the same existing feather icon. The launcher reuses icon index 0 from the bundled Tk DLL; the former Startup watcher is retired. Normal desktop use has one launcher; closing the app stops capture and its two speech containers. The older project-owned Stop desktop link is removed, while Stop-Dictation.ps1 remains available for optional backend shutdown. The feather icon and speech/model configuration remain unchanged by the shutdown follow-up.

## Exit ownership and v1.0 gate

The latest direction requires no dictation-owned background processes after exit. Normal shutdown verifies both scoped containers are stopped; a process-handle supervisor covers abnormal owner termination and then exits. Only services with this project's Compose label and the allowlisted dictation/whisper service label are stopped. Other local AI containers and the shared Docker engine remain outside this app's ownership.

The simplified interface needs no feature expansion for v1.0. Actual packaged normal/forced-exit cleanup and close/reopen checks passed. The remaining release gate is real microphone-to-intended-application acceptance after the earlier input regressions, including a continuous listening/off/on trial. Record those results before calling v1.0 ready. General OS failure, a stopped Docker daemon or a forcibly killed cleanup helper cannot be guaranteed away; cleanup failures are not reported as success.

Packaged lifecycle acceptance uses DICTATION_LIFECYCLE_TEST=1 with unittest discover -s tests -p test_packaged_lifecycle.py. It starts the current package twice, opens no microphone, closes only its own window in the normal case and terminates only its own process in the forced case. Both cases verified no running dictation containers or project helper processes and preservation of unrelated container IDs. The inherited singleton guard and launcher wait also prevent a new owner from starting while prior cleanup is finishing. The installer removes the old resident Startup watcher; final installed state is closed with no dictation-owned services running.
