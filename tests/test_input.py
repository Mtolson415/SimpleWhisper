import ctypes
import sys
import unittest
from unittest.mock import Mock, patch

if sys.platform == 'win32':
    from windows_input import Input, paste_shortcut


@unittest.skipUnless(sys.platform == 'win32', 'Windows input ABI')
class InputTests(unittest.TestCase):
    def test_native_batch_has_correct_size_and_never_submits(self):
        user = Mock()
        user.SendInput.return_value = 4
        with patch('windows_input.ctypes.WinDLL', return_value=user):
            paste_shortcut()
        count, inputs, size = user.SendInput.call_args.args
        self.assertEqual(count, 4)
        self.assertEqual(size, 40 if ctypes.sizeof(ctypes.c_void_p) == 8 else 28)
        self.assertEqual([(i.data.keyboard.vk, i.data.keyboard.flags) for i in inputs],
                         [(0x11, 0), (ord('V'), 0), (ord('V'), 2), (0x11, 2)])

    def test_partial_input_releases_keys_and_reports_failure(self):
        user = Mock()
        user.SendInput.side_effect = [1, 2]
        with patch('windows_input.ctypes.WinDLL', return_value=user):
            with self.assertRaises(OSError):
                paste_shortcut()
        count, inputs, _ = user.SendInput.call_args.args
        self.assertEqual(count, 2)
        self.assertTrue(all(i.data.keyboard.flags == 2 for i in inputs))
