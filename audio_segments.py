"""Bounded, in-memory phrase segmentation for incremental CPU dictation."""
from array import array
import math


class PhraseBuffer:
    def __init__(self, rate=16000, pause=0.6, maximum=8, threshold=180):
        self.rate = rate
        self.pause_frames = int(rate * pause)
        self.maximum_bytes = int(rate * maximum * 2)
        self.threshold = threshold
        self.buffer = bytearray()
        self.speech = False
        self.silence_frames = 0

    def add(self, pcm):
        samples = array('h')
        samples.frombytes(pcm)
        rms = math.sqrt(sum(value * value for value in samples) / max(1, len(samples)))
        voiced = rms >= self.threshold
        self.buffer.extend(pcm)
        self.speech = self.speech or voiced
        self.silence_frames = 0 if voiced else self.silence_frames + len(samples)
        if not self.speech:
            # Keep only 200 ms of pre-roll instead of transcribing silence.
            self.buffer = self.buffer[-int(self.rate * 0.2) * 2:]
        elif self.silence_frames >= self.pause_frames or len(self.buffer) >= self.maximum_bytes:
            return self.flush()
        return None

    def flush(self):
        result = bytes(self.buffer) if self.speech else None
        self.buffer.clear()
        self.speech = False
        self.silence_frames = 0
        return result


class AudioRouter:
    """Single-worker phrase routing; changing session/destination discards old audio."""
    def __init__(self):
        self.context = None
        self.buffer = PhraseBuffer()

    def feed(self, session, target, pcm):
        if pcm is None:
            if self.context and self.context[0] == session:
                phrase = self.buffer.flush()
                if phrase:
                    return self.context[1], phrase
            return None
        if (session, target) != self.context:
            self.context = (session, target)
            self.buffer = PhraseBuffer()
        if target is not None:
            phrase = self.buffer.add(pcm)
            if phrase:
                return target, phrase
        return None
