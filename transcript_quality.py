"""Fast, deterministic recognition-marker cleanup; never a semantic rewrite."""
import re

_MARKERS = re.compile(r'\[\s*(?:blank[\s_]*audio|no[\s_]*speech|silence|music)\s*\]', re.IGNORECASE)
_TOKENS = re.compile(r'<\|(?:endoftext|startoftranscript|nospeech|notimestamps|transcribe|en|es|\d+\.\d+)\|>', re.IGNORECASE)


def clean_transcript(text):
    result = _TOKENS.sub('', _MARKERS.sub('', text))
    if result != text:
        result = re.sub(r'[ \t]{2,}', ' ', result)
        result = re.sub(r'[ \t]+([,.;:!?])', r'\1', result)
    return result.strip()
