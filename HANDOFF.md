# Current handoff - November 12, 2026

## 0.5.0 - simplified direct dictation

The latest user request supersedes the 0.3/0.4 direction: remove the app transcript/copy workflow, rolling revisions and background lock; provide a small dark always-on-top listener with one toggle, a green/red microphone indicator, a settings menu and no listening timeout.

Implemented one final-phrase path to the active external native destination. Ordinary clicks on the toolbar do not activate it. All companion-process windows are excluded as destinations. No transcript widget, copy action, field rewrite, UI Automation dependency, auto-stop selector or review-only toggle remains. Microphone/model choices persist locally; listening starts off. Settings are changed while off. Clipboard transport is internal.

The callback copies/queues raw frames; workers handle phrase detection and inference. Requests and queues are bounded without a total session deadline. Stale destination/session results are discarded without permanently disabling subsequent speech. Logical fields sharing a native input handle cannot always be distinguished.

The primary-source review is docs/IMPLEMENTATION-REVIEW.md. It led to a window-style refresh correction, focus-transition guards and moving phrase detection outside the callback.

41 ordinary Windows checks passed, with one interactive check skipped. That owned two-window check also passed separately: real toggle-click focus preservation, Unicode input, stale-result rejection and fresh input in the second window. No microphone was opened and no user app was automated. Containerized Linux passed 23 checks and skipped 19 Windows/interactive checks. The portable Windows build passed. Preference tests use a small isolated /tmp tmpfs while the rest of the test container remains read-only. Hosted results must be checked separately after pushing.

Microphone quality, actual intended-app acceptance, prolonged hardware stability, reboot/offline and second-host recovery remain unverified. Do not describe synthetic transport checks as universal dictation acceptance.

Public/private ownership remains docs/REPOSITORIES.md. The launcher should resolve portable/v0.5.0. Earlier source/portable versions remain recovery history. Never commit local settings, recordings, transcripts, raw conversations, credentials, weights or backups. Pull shared guidance before subsequent work.

Desktop shortcut follow-up: the user explicitly selected the same existing feather icon. The launcher and Startup watcher reuse icon index 0 from the bundled Tk DLL. Normal desktop use has one launcher; closing the app stops capture. The older project-owned Stop desktop link is removed, while Stop-Dictation.ps1 remains available for optional backend shutdown. No listener behavior or speech/model configuration changed in this follow-up.
