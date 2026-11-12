"""Persist microphone/model choices only. Listening and text are never saved."""
import json
import os
from pathlib import Path

MODELS = {'base', 'base-en', 'turbo'}


def settings_path():
    return Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'LocalWhisperDictation' / 'settings.json'


def load(path=None):
    try:
        data = json.loads((path or settings_path()).read_text(encoding='utf-8'))
        if not isinstance(data, dict):
            return {}
        return {key: value for key, value in data.items()
                if (key == 'microphone' and isinstance(value, str) and len(value) <= 300)
                or (key == 'model' and isinstance(value, str) and value in MODELS)}
    except (OSError, ValueError, TypeError):
        return {}


def save(microphone, model, path=None):
    path = path or settings_path()
    data = {'microphone': microphone, 'model': model if model in MODELS else 'base'}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding='utf-8')
