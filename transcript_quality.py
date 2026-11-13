"""Deterministic recognition-marker and pause-ellipsis cleanup."""
import re

_MARKERS = re.compile(r'\[\s*(?:blank[\s_]*audio|no[\s_]*speech|silence|music)\s*\]', re.IGNORECASE)
_TOKENS = re.compile(r'<\|(?:endoftext|startoftranscript|nospeech|notimestamps|transcribe|en|es|\d+\.\d+)\|>', re.IGNORECASE)
_ELLIPSES = re.compile(r'\.{3,}|\u2026+')


def clean_transcript(text):
    result = _ELLIPSES.sub(' ', _TOKENS.sub('', _MARKERS.sub('', text)))
    if result != text:
        result = re.sub(r'[ \t]{2,}', ' ', result)
        result = re.sub(r'[ \t]+([,.;:!?])', r'\1', result)
    return result.strip()
