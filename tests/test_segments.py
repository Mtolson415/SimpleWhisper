import unittest
from array import array
from audio_segments import PhraseBuffer


def pcm(value, seconds):
    return array('h', [value] * int(16000 * seconds)).tobytes()


class PhraseTests(unittest.TestCase):
    def test_silence_never_becomes_a_phrase(self):
        buffer = PhraseBuffer()
        for _ in range(20):
            self.assertIsNone(buffer.add(pcm(0, 0.5)))
        self.assertLessEqual(len(buffer.buffer), 6400)
        self.assertIsNone(buffer.flush())

    def test_phrase_emits_after_a_pause(self):
        buffer = PhraseBuffer()
        self.assertIsNone(buffer.add(pcm(1000, 1)))
        self.assertIsNone(buffer.add(pcm(0, 0.3)))
        self.assertIsNotNone(buffer.add(pcm(0, 0.3)))
        self.assertIsNone(buffer.flush())

    def test_continuous_speech_is_bounded(self):
        buffer = PhraseBuffer(maximum=2)
        self.assertIsNone(buffer.add(pcm(1000, 1)))
        self.assertIsNotNone(buffer.add(pcm(1000, 1)))

    def test_stop_flushes_unfinished_speech(self):
        buffer = PhraseBuffer()
        buffer.add(pcm(1000, 0.5))
        self.assertEqual(buffer.flush(), pcm(1000, 0.5))
