"""Opt-in native routing acceptance: two owned fields plus a real toolbar click.

No microphone is opened. Focus the synthetic destination, then click the
synthetic toolbar switch when requested. Never targets any user application.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest
from unittest.mock import Mock, patch

@unittest.skipUnless(sys.platform == 'win32' and os.getenv('DICTATION_DESKTOP_TEST') == '1',
                     'Opt-in Windows two-field toolbar acceptance')
class ScratchFieldAcceptance(unittest.TestCase):
    def test_toolbar_preserves_focus_and_routes_only_to_external_fields(self):
        from dictation import App
        import ctypes
        from ctypes import wintypes
        process = subprocess.Popen([sys.executable, str(Path(__file__).parent / 'fixtures/focus_fixture.py')],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, encoding='utf-8')
        def close_fixture():
            try:
                process.stdin.write('close\n'); process.stdin.flush()
                process.wait(timeout=3)
            except (OSError, subprocess.TimeoutExpired):
                process.terminate(); process.wait(timeout=3)
            finally:
                process.stdin.close(); process.stdout.close()
        self.addCleanup(close_fixture)
        fixture_pid = json.loads(process.stdout.readline())['pid']
        with patch('dictation.threading.Thread.start'), patch('dictation.preferences.load', return_value={}), \
                patch('dictation.sd.query_devices', return_value=[]), patch('dictation.sd.RawInputStream', return_value=Mock()):
            app = App()
            self.addCleanup(app.root.destroy)
            app.root.title('Dictation synthetic toolbar')
            app.busy = False
            app.note = 'Synthetic test: no microphone is opened'
            app.draw()
            deadline = time.monotonic() + 45
            target = None
            print('Focus Dictation synthetic destination; the test clicks its own toolbar without opening a microphone.', flush=True)
            while time.monotonic() < deadline:
                app.root.update()
                current = app.desktop.destination()
                owner = wintypes.DWORD()
                if current is not None:
                    app.user.GetWindowThreadProcessId(current[0], ctypes.byref(owner))
                if current is not None and owner.value == fixture_pid:
                    for _ in range(10):
                        app.root.update()
                        time.sleep(0.02)
                    current = app.desktop.destination()
                    if current is None:
                        continue
                    app.user.GetWindowThreadProcessId(current[0], ctypes.byref(owner))
                    if owner.value != fixture_pid:
                        continue
                    target = current
                    # Actual mouse input into this test's own nonactivating toolbar.
                    # Unlike app-targeted automation, this does not preactivate it.
                    app.user.SetCursorPos(app.root.winfo_rootx() + 36, app.root.winfo_rooty() + 37)
                    app.user.mouse_event(2, 0, 0, 0, 0)
                    app.user.mouse_event(4, 0, 0, 0, 0)
                    for _ in range(10):
                        app.root.update()
                        time.sleep(0.02)
                    break
                time.sleep(0.02)
            self.assertTrue(app.listening, 'Click the synthetic toolbar switch within 45 seconds')
            self.assertIsNotNone(target)
            self.assertEqual(app.desktop.destination(), target, 'Toolbar click stole the active text box')
            self.assertTrue(app.deliver(app.session, target, 'Hello, español.'))
            time.sleep(0.15)
            process.stdin.write('read\n'); process.stdin.flush()
            self.assertEqual(json.loads(process.stdout.readline()), ['Synthetic prefix: Hello, español. ', ''])
            process.stdin.write('second\n'); process.stdin.flush()
            self.assertEqual(process.stdout.readline().strip(), 'ready')
            deadline = time.monotonic() + 2
            next_target = app.desktop.destination()
            while next_target == target and time.monotonic() < deadline:
                app.root.update()
                time.sleep(0.02)
                next_target = app.desktop.destination()
            self.assertIsNotNone(next_target)
            self.assertNotEqual(next_target, target)
            self.assertFalse(app.deliver(app.session, target, 'Stale text must not appear'))
            self.assertTrue(app.deliver(app.session, next_target, 'Second field'))
            time.sleep(0.15)
            process.stdin.write('read\n'); process.stdin.flush()
            self.assertEqual(json.loads(process.stdout.readline()),
                ['Synthetic prefix: Hello, español. ', 'Second field '])
            app.stop()
