"""Desktop guard behavior with fake Win32 calls; no user keystrokes emitted."""
import io
import sys
import unittest
import wave
from unittest.mock import Mock

if sys.platform == 'win32':
    from dictation import App, wav_bytes


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
        return app

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

    def test_recording_encoding_matches_gateway(self):
        with wave.open(io.BytesIO(wav_bytes(b'\0\0' * 16000)), 'rb') as audio:
            self.assertEqual((audio.getnchannels(), audio.getsampwidth(), audio.getframerate()), (1, 2, 16000))
            self.assertEqual(audio.getnframes(), 16000)
