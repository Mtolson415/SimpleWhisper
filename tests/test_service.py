import io
import unittest
import wave
from unittest.mock import patch

from service import transcribe, validate_audio


def sample(rate=16000, channels=1, duration=1):
    data = io.BytesIO()
    with wave.open(data, 'wb') as out:
        out.setnchannels(channels)
        out.setsampwidth(2)
        out.setframerate(rate)
        out.writeframes(b'\0\0' * rate * channels * duration)
    return data.getvalue()


class AudioTests(unittest.TestCase):
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
