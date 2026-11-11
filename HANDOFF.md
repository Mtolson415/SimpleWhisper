# Dictation handoff - 2026-11-11

Public/private ownership is in docs/REPOSITORIES.md. Read AGENTS.md and docs/README.md before work.

## Current milestone: 0.3.1

Compact two-column companion layout, corrected active-text-box label, scrollable transcript, bounded pending live phrases while shortcut keys are held, and checked native paste input. The versioned portable build and launcher resolve 0.3.1. Existing continuous listening, auto-stop, quality filtering and optional verified rolling revisions are retained in this source milestone.

Validation: 51 Windows unit checks passed plus one opt-in real scratch-field acceptance check. Containerized Linux: 28 passed, 24 skipped. Portable build passed. The compact interface was visually checked. Synthetic Unicode insertion preserved existing text. No Enter is sent.

Real microphone dictation into the user's intended app, every browser/Word field, reboot/offline behavior and second-host recovery remain unverified. Restart recording after changing target windows. Unsupported/elevated fields may require manual copying. No recordings, transcripts or model weights are tracked.

## Focus-guard correction (0.3.2)

User-reported failure: recognition reached the preview but status said Window changed. The older stop-to-transcribe default and the newer continuous-live default handled a window switch differently: live mode permanently latched paste suppression for that session. Version 0.3.2 pauses ordinary live insertion only while away from the original window, resumes new phrases upon return, and discards pending pastes on a switch rather than replaying them. Rolling draft revision stops remain strict because they protect previously inserted text. Starting a direct-input recording while the companion itself is focused now asks the user to click the intended destination first.

The native clipboard and checked paste batch are retained: the reported status shows paste was blocked before either was called. The earlier scratch-field success did not verify this focus-transition path or Codex compatibility. New regression tests exercise pause/return/resume, no insertion into a different window, and the companion-start guard. Codex microphone-to-chat acceptance remains user verification; do not describe it as passed.

## Current milestone: 0.4.0 - destination behavior

The related chat Use your STT model for dictation was reviewed: continuous listening, English/Spanish model selection, fast rolling hypotheses with optional later revisions, marker filtering, auto-stop and always-on-top remain requirements. The current user additionally requested an optional text-box lock that keeps sending to the captured field after focus moves elsewhere, until recording stops. Lock off follows active fields. Do not regress this to a permanent window-change paste suppression.

Implemented capability-checked background updates for plain editable fields, guarded prefix/suffix preservation and last-draft revisions. Unsupported fields report the limitation and retain preview text; no silent background redirection. Provider-induced focus changes are restored, but may be visible. Rolling remains optional/off by default and ordinary insertion is independent. No universal Codex/browser/Word background support is claimed.

Validation: 67 ordinary Windows checks passed (two opt-in skips); Linux 37 passed / 32 skipped. The real owned WPF two-field test passed insertion, revision, unchanged second field and restored focus. No user app was automated in that test and no microphone was opened. User microphone-to-textbox acceptance remains outstanding.
