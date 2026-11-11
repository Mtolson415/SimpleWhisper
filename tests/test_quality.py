import unittest
from transcript_quality import clean_transcript


class QualityTests(unittest.TestCase):
    def test_marker_is_removed_inside_spoken_text(self):
        self.assertEqual(clean_transcript('Hello [BLANK_AUDIO] world.'), 'Hello world.')

    def test_variants_and_marker_only_audio_are_empty(self):
        for text in ['[BLANK_AUDIO]', '[blank audio]', '[ NO_SPEECH ]', '[silence]', '<|nospeech|>']:
            self.assertEqual(clean_transcript(text), '')

    def test_real_bracketed_text_and_spanish_are_preserved(self):
        text = 'Hola [opcional], cuesta $25. Use array[0] and [x].'
        self.assertEqual(clean_transcript(text), text)

    def test_whisper_control_tokens_are_removed(self):
        self.assertEqual(clean_transcript('<|en|>Hello<|1.23|><|endoftext|>'), 'Hello')
