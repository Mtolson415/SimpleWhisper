# Release checklist

## Publishing a release

Before publishing a release:

- [ ] Public branch checks pass for the exact packaged source commit.
- [ ] Windows artifact includes launch scripts, Docker files, model lock, docs/assets, license/notices and runtime licenses.
- [ ] ZIP excludes models, `.env`, recordings, transcripts and private operational data.
- [ ] Verify ZIP SHA256; publish ZIP plus SHA256SUMS.txt and release notes.
- [ ] Verify tag/asset visibility and update private PUBLIC_TOOL_REF.json with exact source/run/hash.
- [ ] Verify paired repository visibility, commits and checks; update handoffs.

Completion evidence belongs in the handoff/private release record; this reusable checklist is not a claim that unchecked work was completed.

Keep captured speech, logs, user data and secrets out of all Git repositories.
