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

    def test_pause_ellipses_join_words_without_running_them_together(self):
        for text in ('Hello...world.', 'Hello ... world.', 'Hello\u2026world.'):
            self.assertEqual(clean_transcript(text), 'Hello world.')
        self.assertEqual(clean_transcript('...Hello world....'), 'Hello world')

    def test_ellipsis_only_pause_is_empty(self):
        for text in ('...', '\u2026', '......', ' ... \u2026 '):
            self.assertEqual(clean_transcript(text), '')

    def test_other_punctuation_and_decimals_are_preserved(self):
        text = 'Version 0.5.3 costs 1.25. Really? Yes! Hola, mundo.'
        self.assertEqual(clean_transcript(text), text)
