import io
import unittest
import wave
from unittest.mock import patch

import service
from service import transcribe, validate_audio, select_model, model_catalog


def sample(rate=16000, channels=1, duration=1):
    data = io.BytesIO()
    with wave.open(data, 'wb') as out:
        out.setnchannels(channels)
        out.setsampwidth(2)
        out.setframerate(rate)
        out.writeframes(b'\0\0' * rate * channels * duration)
    return data.getvalue()


class AudioTests(unittest.TestCase):
    def test_catalog_does_not_expose_paths(self):
        catalog = model_catalog()
        self.assertEqual(len(catalog['models']), 3)
        self.assertTrue(all(set(model) == {'id', 'label'} for model in catalog['models']))

    def test_unknown_model_never_reaches_runtime(self):
        with patch('service.urllib.request.urlopen') as upstream:
            with self.assertRaises(ValueError):
                select_model('../../outside.bin')
            upstream.assert_not_called()

    def test_failed_model_load_does_not_change_active_model(self):
        original = service.ACTIVE_MODEL
        with patch('service.urllib.request.urlopen', side_effect=OSError('offline')):
            with self.assertRaises(OSError):
                select_model('turbo')
        self.assertEqual(service.ACTIVE_MODEL, original)

    def test_valid_pcm(self):
        validate_audio(sample())

    def test_rejects_stereo_and_wrong_rate(self):
        for audio in (sample(channels=2), sample(rate=8000)):
            with self.assertRaises(ValueError):
                validate_audio(audio)

    def test_rejects_truncated_frames(self):
        with self.assertRaises(ValueError):
            validate_audio(sample()[:-10])

    def test_rejects_empty_and_overlong(self):
        for length in (0, 121):
            with self.assertRaises(ValueError):
                validate_audio(sample(duration=length))

    def test_invalid_audio_never_reaches_model(self):
        with patch('service.urllib.request.urlopen') as upstream:
            with self.assertRaises((wave.Error, EOFError)):
                transcribe(b'not audio')
            upstream.assert_not_called()


if __name__ == '__main__':
    unittest.main()
