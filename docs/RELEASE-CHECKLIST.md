# Release checklist

## 0.5.2 scope

User-reported tested and working on November 12, 2026. Application names, duration and language coverage were not provided. Ordinary local Windows tests: 56 passed, two opt-in checks skipped. Historical desktop/lifecycle evidence is in HANDOFF.md. Do not equate these with universal application acceptance.

Before publishing a release:

- [ ] Public branch checks pass for the exact packaged source commit.
- [ ] Windows artifact includes launch scripts, Docker files, model lock, docs/assets, license/notices and runtime licenses.
- [ ] ZIP excludes models, `.env`, recordings, transcripts and private operational data.
- [ ] Verify ZIP SHA256; publish ZIP plus SHA256SUMS.txt and release notes.
- [ ] Verify tag/asset visibility and update private PUBLIC_TOOL_REF.json with exact source/run/hash.
- [ ] Verify paired repository visibility, commits and checks; update handoffs.

Completion evidence belongs in the handoff/private release record; this reusable checklist is not a claim that unchecked work was completed.

## Before v1.0

- [ ] Record real microphone results by app/version, language and microphone, without retaining speech or dictated text.
- [ ] Record continuous listening, explicit off/on and intended-app insertion checks.
- [ ] Check current packaged normal close, forced termination and reopen with unrelated containers preserved.
- [ ] Check first installation on a clean second host and document model/setup failures.
- [ ] Check reboot and disconnected operation, keeping those claims separate.
- [ ] Review third-party license distribution and public documentation against shipped files.

Limit scope honestly if any item is deferred. Keep captured speech, logs, user data and secrets out of all Git repositories.
