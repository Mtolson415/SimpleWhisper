import unittest
from array import array
from rolling_audio import RollingPhraseBuffer, LatestJobs


class RollingTests(unittest.TestCase):
    def test_snapshot_does_not_wait_for_silence(self):
        buffer = RollingPhraseBuffer()
        pcm = array('h', [1000] * 16000).tobytes()
        first = buffer.feed(pcm)
        second = buffer.feed(pcm)
        self.assertFalse(first['final'])
        self.assertEqual(first['phrase'], second['phrase'])
        self.assertGreater(len(second['audio']), len(first['audio']))
        self.assertTrue(buffer.finish()['final'])

    def test_silence_never_creates_snapshots(self):
        buffer = RollingPhraseBuffer()
        self.assertIsNone(buffer.feed(b'\0\0' * 32000))

    def test_pending_partial_is_replaced_by_final(self):
        jobs = LatestJobs()
        jobs.put({'phrase': 0, 'audio': b'old', 'final': False})
        jobs.put({'phrase': 0, 'audio': b'latest', 'final': True})
        jobs.put(None)
        self.assertEqual(jobs.get()['audio'], b'latest')
        self.assertIsNone(jobs.get())

    def test_queue_has_a_fixed_bound(self):
        jobs = LatestJobs(maximum=3)
        for index in range(10):
            jobs.put({'phrase': index, 'audio': b'x', 'final': True})
        self.assertEqual(len(jobs.jobs), 3)
