import json
from pathlib import Path
import tempfile
import unittest
import preferences

class PreferenceTests(unittest.TestCase):
    def test_only_microphone_and_allowlisted_model_are_loaded(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'settings.json'
            path.write_text(json.dumps({'microphone':'Synthetic input', 'model':'base-en', 'listening':True,
                                        'transcript':'never load'}), encoding='utf-8')
            self.assertEqual(preferences.load(path), {'microphone':'Synthetic input', 'model':'base-en'})

    def test_invalid_settings_fall_back_to_defaults(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'settings.json'
            path.write_text('{broken', encoding='utf-8')
            self.assertEqual(preferences.load(path), {})
            path.write_text('{"model": [], "microphone": 4}', encoding='utf-8')
            self.assertEqual(preferences.load(path), {})

    def test_saved_choices_never_include_text_or_listening(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'settings.json'
            preferences.save('Synthetic input', 'turbo', path)
            self.assertEqual(json.loads(path.read_text(encoding='utf-8')),
                             {'microphone':'Synthetic input','model':'turbo'})
