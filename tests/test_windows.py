"""Routing and lifecycle checks. No user keystrokes or microphone are used."""
from collections import deque
import io
import queue
import sys
import unittest
import wave
from unittest.mock import Mock, patch
if sys.platform == 'win32':
    from dictation import App, wav_bytes, gateway_running
    from windows_focus import Desktop

@unittest.skipUnless(sys.platform == 'win32', 'Windows companion')
class DesktopTests(unittest.TestCase):
    def setUp(self):
        self.clip_patch = patch('dictation.set_clipboard_text')
        self.clip = self.clip_patch.start()
        self.addCleanup(self.clip_patch.stop)
        self.key_patch = patch('dictation.paste_shortcut')
        self.keys = self.key_patch.start()
        self.addCleanup(self.key_patch.stop)

    def app(self):
        app = App.__new__(App)
        app.desktop = Mock()
        app.desktop.destination.return_value = (123, 124)
        app.desktop.keys_held.return_value = False
        app.own_window = 999
        app.session = 1
        app.pending = deque()
        app.listening = True
        app.note = ''
        return app

    def test_paste_into_unchanged_external_destination(self):
        app = self.app()
        self.assertTrue(app.deliver(1, (123, 124), 'Synthetic phrase'))
        self.clip.assert_called_once_with(999, 'Synthetic phrase ')
        self.keys.assert_called_once_with()

    def test_focus_switch_discards_old_phrase_without_disabling_listener(self):
        app = self.app()
        app.desktop.destination.return_value = (123, 125)
        self.assertFalse(app.deliver(1, (123, 124), 'old phrase'))
        self.clip.assert_not_called()
        self.assertTrue(app.listening)
        self.assertTrue(app.deliver(1, (123, 125), 'new phrase'))

    def test_helper_or_settings_cannot_receive_dictation(self):
        app = self.app()
        app.desktop.destination.return_value = None
        self.assertFalse(app.deliver(1, (123, 124), 'phrase'))
        self.assertFalse(app.deliver(1, None, 'phrase'))
        self.keys.assert_not_called()

    def test_focus_change_during_clipboard_write_prevents_paste(self):
        app = self.app()
        app.desktop.destination.side_effect = [(123, 124), (123, 125)]
        self.assertFalse(app.deliver(1, (123, 124), 'phrase'))
        self.keys.assert_not_called()

    def test_old_session_cannot_insert_into_new_session(self):
        app = self.app()
        self.assertFalse(app.deliver(0, (123, 124), 'old phrase'))
        self.clip.assert_not_called()

    def test_markers_do_not_reach_clipboard(self):
        app = self.app()
        self.assertFalse(app.deliver(1, (123, 124), '[BLANK_AUDIO]'))
        self.clip.assert_not_called()

    def test_held_keys_queue_phrase_without_stopping(self):
        app = self.app()
        app.desktop.keys_held.return_value = True
        app.deliver(1, (123, 124), 'phrase')
        self.assertEqual(len(app.pending), 1)
        self.keys.assert_not_called()
        app.desktop.keys_held.return_value = False
        self.assertTrue(app.deliver(*app.pending.popleft()))

    def test_pending_input_is_bounded(self):
        app = self.app()
        app.desktop.keys_held.return_value = True
        for _ in range(30):
            app.deliver(1, (123, 124), 'phrase')
        self.assertEqual(len(app.pending), 16)
        self.assertTrue(app.listening)

    def test_blocked_input_does_not_stop_listener(self):
        app = self.app()
        self.keys.side_effect = OSError('blocked')
        self.assertFalse(app.deliver(1, (123, 124), 'phrase'))
        self.assertTrue(app.listening)
        self.assertIn('blocked', app.note)

    def test_audio_has_no_session_duration_limit(self):
        app = self.app()
        app.active_target = (123, 124)
        app.audio_frames = queue.Queue(maxsize=128)
        app.events = queue.Queue()
        for _ in range(100):
            app.audio(b'\0\0' * 1600, 16000 * 3600, None, False)
        self.assertEqual(app.audio_frames.qsize(), 100)
        self.assertTrue(app.listening)
        self.assertTrue(app.events.empty())

    def test_audio_while_settings_focused_is_discarded(self):
        app = self.app()
        app.active_target = None
        app.audio_frames = queue.Queue(maxsize=128)
        app.events = queue.Queue()
        app.audio(b'\0\0', 1, None, False)
        self.assertEqual(app.audio_frames.get_nowait(), (1, None, b''))

    def test_queue_full_warns_without_stopping(self):
        app = self.app()
        app.jobs = queue.Queue(maxsize=1)
        app.events = queue.Queue()
        app.submit(b'audio', (123, 124))
        app.submit(b'more audio', (123, 124))
        self.assertTrue(app.listening)
        self.assertEqual(app.events.get_nowait()[0], 'warning')

    def test_docker_unknown_is_not_a_confirmed_stop(self):
        with patch('dictation.subprocess.run', side_effect=OSError()):
            self.assertIsNone(gateway_running())

    def test_both_containers_required(self):
        with patch('dictation.subprocess.run', return_value=Mock(returncode=0, stdout='dictation\nwhisper\n')):
            self.assertTrue(gateway_running())
        with patch('dictation.subprocess.run', return_value=Mock(returncode=0, stdout='dictation\n')):
            self.assertFalse(gateway_running())

    def test_wav_encoding(self):
        with wave.open(io.BytesIO(wav_bytes(b'\0\0' * 16000)), 'rb') as audio:
            self.assertEqual((audio.getnchannels(), audio.getsampwidth(), audio.getframerate()), (1, 2, 16000))

    def test_toolbar_is_nonactivating_and_topmost(self):
        desktop = Desktop.__new__(Desktop)
        desktop.user = Mock()
        desktop.user.GetAncestor.return_value = 77
        desktop.get_style = Mock(return_value=0)
        desktop.set_style = Mock()
        widget = Mock()
        widget.winfo_id.return_value = 76
        with patch('windows_focus.ctypes.WinDLL', side_effect=OSError()):
            self.assertEqual(desktop.toolbar(widget), 77)
        flags = desktop.set_style.call_args.args[2]
        self.assertTrue(flags & 0x08000000)
        self.assertTrue(flags & 0x80)
        desktop.user.SetWindowPos.assert_called_once()
