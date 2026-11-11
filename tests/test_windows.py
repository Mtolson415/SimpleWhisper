"""Desktop guard behavior with fake Win32 calls; no user keystrokes emitted."""
import io
import queue
import sys
import unittest
import wave
from unittest.mock import Mock, patch

if sys.platform == 'win32':
    from dictation import App, wav_bytes, gateway_running


@unittest.skipUnless(sys.platform == 'win32', 'Windows helper test')
class DesktopTests(unittest.TestCase):
    def app(self):
        app = App.__new__(App)
        app.target = 123
        app.user = Mock()
        app.user.GetForegroundWindow.return_value = 123
        app.user.GetAsyncKeyState.return_value = 0
        app.root = Mock()
        app.status = Mock()
        app.copy = Mock()
        app.busy = True
        app.direct_input = Mock()
        app.direct_input.get.return_value = True
        return app

    def test_unchecked_direct_input_keeps_clipboard_and_keyboard_untouched(self):
        app = self.app()
        app.direct_input.get.return_value = False
        app.insert('Synthetic test')
        app.copy.assert_not_called()
        app.user.keybd_event.assert_not_called()
        app.user.GetForegroundWindow.assert_not_called()
        self.assertFalse(app.busy)

    def test_window_switch_prevents_clipboard_and_paste(self):
        app = self.app()
        app.user.GetForegroundWindow.return_value = 456
        app.insert('Synthetic test')
        app.copy.assert_not_called()
        app.user.keybd_event.assert_not_called()
        self.assertFalse(app.busy)

    def test_held_modifiers_delay_paste(self):
        app = self.app()
        app.user.GetAsyncKeyState.return_value = 0x8000
        app.insert('Synthetic test')
        app.root.after.assert_called_once()
        app.copy.assert_not_called()
        app.user.keybd_event.assert_not_called()

    def test_paste_does_not_send_enter(self):
        app = self.app()
        app.insert('Synthetic test')
        app.copy.assert_called_once()
        keys = [call.args[0] for call in app.user.keybd_event.call_args_list]
        self.assertEqual(keys, [0x11, ord('V'), ord('V'), 0x11])
        self.assertFalse(app.busy)

    def test_live_paste_copies_only_new_phrase_and_keeps_busy_state(self):
        app = self.app()
        app.live_paste_suppressed = False
        app.stream = Mock()
        app.insert(' new phrase', live=True)
        app.copy.assert_called_once_with(' new phrase')
        self.assertTrue(app.busy)

    def test_live_window_switch_suppresses_rest_of_session(self):
        app = self.app()
        app.live_paste_suppressed = False
        app.user.GetForegroundWindow.return_value = 456
        app.insert('first phrase', live=True)
        app.user.GetForegroundWindow.return_value = 123
        app.insert('later phrase', live=True)
        app.copy.assert_not_called()
        app.user.keybd_event.assert_not_called()

    def test_recording_encoding_matches_gateway(self):
        with wave.open(io.BytesIO(wav_bytes(b'\0\0' * 16000)), 'rb') as audio:
            self.assertEqual((audio.getnchannels(), audio.getsampwidth(), audio.getframerate()), (1, 2, 16000))
            self.assertEqual(audio.getnframes(), 16000)

    def test_container_stop_requests_companion_close(self):
        app = self.app()
        app.events = queue.Queue()
        with patch('dictation.gateway_running', side_effect=[True, False]), patch('dictation.time.sleep'):
            app.monitor_container()
        self.assertEqual(app.events.get_nowait(), ('container_stopped', None))

    def test_docker_failure_is_treated_as_stopped(self):
        with patch('dictation.subprocess.run', side_effect=OSError('Docker unavailable')):
            self.assertFalse(gateway_running())

    def test_container_detection_uses_project_and_service_labels(self):
        with patch('dictation.subprocess.run', return_value=Mock(returncode=0, stdout='dictation\nwhisper\n')) as run:
            self.assertTrue(gateway_running())
        command = run.call_args.args[0]
        self.assertIn('label=com.docker.compose.project=local-whisper-dictation', command)
        self.assertIn('{{.Label "com.docker.compose.service"}}', command)

    def test_model_container_stop_is_also_detected(self):
        with patch('dictation.subprocess.run', return_value=Mock(returncode=0, stdout='dictation\n')):
            self.assertFalse(gateway_running())
