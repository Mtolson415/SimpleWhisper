# Dictation handoff - 2026-11-11

Public/private ownership is in docs/REPOSITORIES.md. Read AGENTS.md and docs/README.md before work.

## Current milestone: 0.3.1

Compact two-column companion layout, corrected active-text-box label, scrollable transcript, bounded pending live phrases while shortcut keys are held, and checked native paste input. The versioned portable build and launcher resolve 0.3.1. Existing continuous listening, auto-stop, quality filtering and optional verified rolling revisions are retained in this source milestone.

Validation: 51 Windows unit checks passed plus one opt-in real scratch-field acceptance check. Containerized Linux: 28 passed, 24 skipped. Portable build passed. The compact interface was visually checked. Synthetic Unicode insertion preserved existing text. No Enter is sent.

Real microphone dictation into the user's intended app, every browser/Word field, reboot/offline behavior and second-host recovery remain unverified. Restart recording after changing target windows. Unsupported/elevated fields may require manual copying. No recordings, transcripts or model weights are tracked.
