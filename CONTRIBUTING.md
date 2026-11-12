# Contributing

Read [setup](docs/GETTING-STARTED.md) and the [operating guide](docs/README.md). Focused reliability, accessibility, test and documentation improvements are welcome. Discuss large interface/architecture changes first.

Report bugs through [issue forms](https://github.com/Mtolson415/local-whisper-dictation/issues/new/choose). Include app, Windows/Docker versions, model, reproduction and expected/actual results. Use synthetic text and sanitized logs. Security reports follow [SECURITY.md](SECURITY.md).

## Develop and test

Use Python 3.14 in a separate environment; preserve other installations and caches.

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

[Container and opt-in checks](docs/README.md#tests-and-acceptance) interact with owned windows/services: read instructions first. Ordinary tests do not establish microphone accuracy or universal compatibility.

## Pull requests

Branch from current `main`. Describe the problem, resulting behavior and checks; update docs. Preserve loopback binding, fixed local upstream, bounded input, non-root containers, capture-off startup and scoped cleanup.

Never commit credentials, `.env`, settings, recordings, transcripts, weights, databases, raw conversations or backups. Synthetic audio stays in memory. Follow the [code of conduct](CODE_OF_CONDUCT.md).

Michael Tolson maintains the project. Reviews/support are best effort without response-time guarantees. Contributors need only this public repository. Owner coordination is in the [repository map](docs/REPOSITORIES.md).
