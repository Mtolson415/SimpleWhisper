"""Opt-in real clipboard/input check, restricted to this test's own scratch field.

Run with DICTATION_DESKTOP_TEST=1 on an unlocked Windows desktop.
No microphone is opened, no application data is read, and no Enter is sent.
"""
import os
import sys
import unittest


@unittest.skipUnless(sys.platform == 'win32' and os.getenv('DICTATION_DESKTOP_TEST') == '1',
                     'Opt-in interactive Windows scratch-field test')
class ScratchFieldAcceptance(unittest.TestCase):
    def test_real_unicode_insertion_preserves_existing_text(self):
        import ctypes
        from ctypes import wintypes
        import tkinter as tk
        import time
        from dictation import App

        root = tk.Tk()
        root.title('Dictation synthetic insertion acceptance')
        self.addCleanup(root.destroy)
        field = tk.Text(root)
        field.pack()
        field.insert('1.0', 'Synthetic prefix: ')
        field.mark_set('insert', 'end-1c')
        root.update()
        root.lift()
        field.focus_force()
        root.update()
        user = ctypes.WinDLL('user32', use_last_error=True)
        user.GetForegroundWindow.restype = wintypes.HWND
        user.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
        user.GetAncestor.restype = wintypes.HWND
        target = user.GetAncestor(root.winfo_id(), 2)
        deadline = time.monotonic() + 20
        while user.GetForegroundWindow() != target and time.monotonic() < deadline:
            root.update()
            time.sleep(0.05)
        self.assertEqual(user.GetForegroundWindow(), target,
                         'Scratch field must be foreground; do not paste elsewhere')
        field.focus_force()
        root.update()
        app = App.__new__(App)
        app.root, app.user, app.target = root, user, target
        app.status = tk.StringVar(root)
        app.direct_input = tk.BooleanVar(root, value=True)
        app.busy = True
        app.record_locked = False
        self.assertTrue(app.insert('Hello, español.'))
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            root.update()
            if field.get('1.0', 'end-1c') == 'Synthetic prefix: Hello, español.':
                break
            time.sleep(0.02)
        self.assertEqual(field.get('1.0', 'end-1c'), 'Synthetic prefix: Hello, español.')
