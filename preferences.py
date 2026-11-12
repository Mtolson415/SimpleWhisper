"""Persist microphone/model/shortcut choices. Listening and text are never saved."""
import json
import os
from pathlib import Path

MODELS = {'base', 'base-en', 'turbo'}
DEFAULT_SHORTCUT = 'Ctrl+Alt+D'


def shortcut_parts(value):
    """Only explicit Ctrl/Alt combinations with letters, digits or F1–F12."""
    if not isinstance(value, str):
        raise ValueError('Invalid shortcut')
    parts = value.split('+')
    modifiers, key = parts[:-1], parts[-1]
    if (not modifiers or len(set(modifiers)) != len(modifiers)
            or any(m not in {'Ctrl', 'Alt', 'Shift'} for m in modifiers)
            or not {'Ctrl', 'Alt'}.intersection(modifiers)):
        raise ValueError('Use Ctrl or Alt plus a letter, number or F1–F12')
    if len(key) == 1 and key in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789':
        vk = ord(key)
    elif key in {f'F{i}' for i in range(1, 13)}:
        vk = 0x70 + int(key[1:]) - 1
    else:
        raise ValueError('Use a letter, number or F1–F12')
    return sum({'Ctrl': 2, 'Alt': 1, 'Shift': 4}[m] for m in modifiers), vk


def valid_shortcut(value):
    try:
        shortcut_parts(value)
        return True
    except ValueError:
        return False


def settings_path():
    return Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'LocalWhisperDictation' / 'settings.json'


def load(path=None):
    try:
        data = json.loads((path or settings_path()).read_text(encoding='utf-8'))
        if not isinstance(data, dict):
            return {}
        return ({key: value for key, value in data.items()
                if (key == 'microphone' and isinstance(value, str) and len(value) <= 300)
                or (key == 'model' and isinstance(value, str) and value in MODELS)}
                | ({'shortcut': data['shortcut']} if valid_shortcut(data.get('shortcut')) else {}))
    except (OSError, ValueError, TypeError):
        return {}


def save(microphone, model, path=None, *, shortcut=DEFAULT_SHORTCUT):
    path = path or settings_path()
    data = {'microphone': microphone, 'model': model if model in MODELS else 'base'}
    data['shortcut'] = shortcut if valid_shortcut(shortcut) else DEFAULT_SHORTCUT
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding='utf-8')
