"""Rolling snapshots with coalescing, bounded memory, and final phrase boundaries."""
from collections import deque
import threading
from audio_segments import PhraseBuffer


class RollingPhraseBuffer(PhraseBuffer):
    def __init__(self, interval=1.0, **kwargs):
        super().__init__(**kwargs)
        self.interval_frames = int(self.rate * interval)
        self.since_snapshot = 0
        self.phrase = 0

    def feed(self, pcm):
        self.since_snapshot += len(pcm) // 2
        final = self.add(pcm)
        if final:
            result = {'phrase': self.phrase, 'audio': final, 'final': True}
            self.phrase += 1
            self.since_snapshot = 0
            return result
        if self.speech and self.since_snapshot >= self.interval_frames and len(self.buffer) >= self.rate * 2:
            self.since_snapshot = 0
            return {'phrase': self.phrase, 'audio': bytes(self.buffer), 'final': False}
        return None

    def finish(self):
        audio = self.flush()
        return {'phrase': self.phrase, 'audio': audio, 'final': True} if audio else None


class LatestJobs:
    def __init__(self, maximum=8):
        self.jobs = deque()
        self.maximum = maximum
        self.condition = threading.Condition()

    def put(self, job):
        with self.condition:
            if job is not None:
                for index, old in enumerate(self.jobs):
                    if old is not None and old['phrase'] == job['phrase']:
                        self.jobs[index] = job
                        self.condition.notify()
                        return
            if len(self.jobs) >= self.maximum:
                self.jobs.popleft()
            self.jobs.append(job)
            self.condition.notify()

    def get(self):
        with self.condition:
            while not self.jobs:
                self.condition.wait()
            return self.jobs.popleft()
