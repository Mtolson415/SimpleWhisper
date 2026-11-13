# SimpleWhisper 0.5.2

Local voice dictation for Windows, with a small dark floating toolbar and explicit microphone control.

## Download and setup

Download **SimpleWhisper-Windows-x64.zip** below. Compare its SHA256 with **SHA256SUMS.txt**, extract the whole folder, then follow [Getting started](https://github.com/Mtolson415/local-whisper-dictation/blob/v0.5.2/docs/GETTING-STARTED.md).

Requires Windows 11 x64, Docker Desktop with Linux containers, a microphone and separately obtained model files. The Windows runtime is included. The executable is unsigned. Initial image/model downloads require internet access.

## Highlights

- SimpleWhisper name with matching dark toolbar/settings and the existing feather icon.
- Click the microphone or use a configurable activation shortcut; independent **On top** control.
- English/Spanish Base default, with Base.en and Turbo alternatives.
- Phrase-based local recognition into the active external field, no Enter submission.
- Closing stops the owned speech containers; a lifetime helper handles forced owner termination.
- New illustrated project page, expandable guides, setup documentation and contribution/support routes.

## Verification and limitations

Fresh ordinary Windows tests passed 56 checks with two opt-in skips; hosted Windows/Linux/build evidence is recorded with the release source in the private maintainer record. Previous owned-window and packaged lifecycle results are documented in the public handoff.

Native focus handles cannot distinguish every logical browser field. Recognition can mishear: review text before sending. Clipboard insertion replaces clipboard contents; OS clipboard history/sync and Whisper logs can retain text separately.

This is the current **0.5.2** release; v0.2.0 remains historical. See [CHANGELOG](https://github.com/Mtolson415/local-whisper-dictation/blob/v0.5.2/CHANGELOG.md) and [security policy](https://github.com/Mtolson415/local-whisper-dictation/blob/v0.5.2/SECURITY.md).
