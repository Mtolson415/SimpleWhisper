# Security and privacy

Fixes target the latest published 0.5.x release. Older versions have no parallel backports. No response-time guarantee is offered.

## Report privately

Use [GitHub private vulnerability reporting](https://github.com/Mtolson415/local-whisper-dictation/security/advisories/new) when available. Otherwise request a private channel in an issue **without sensitive details**. Once private, include version, impact and a minimal synthetic reproduction. Never attach recordings, dictated text, private logs or secrets.

## Trust boundaries

- Capture begins only when enabled; the app saves no recordings/history.
- Local endpoints bind to loopback. Do not expose unauthenticated services to a LAN/internet.
- Clipboard insertion overwrites contents. OS history/sync can retain them separately.
- Whisper logs can contain recognized text; keep them private and review retention.
- Native focus checks cannot distinguish every browser field. Keep focus stable and review text.
- Verify model hashes and release checksums. Checksums are integrity checks, not publisher signatures.
- Executables are unsigned. Protected/elevated fields may reject input; the app does not elevate itself.

Never commit secrets/private data, even in private repositories.
