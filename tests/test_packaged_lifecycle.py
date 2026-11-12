"""Opt-in actual package exit checks. Starts/stops only this project's stack.

No microphone is opened. The only window closed belongs to the executable
launched by this test. Refuses to run if a project companion is already open.
"""
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest


@unittest.skipUnless(sys.platform == 'win32' and os.getenv('DICTATION_LIFECYCLE_TEST') == '1',
                     'Opt-in packaged shutdown acceptance')
class PackagedLifecycleTests(unittest.TestCase):
    def test_normal_and_forced_exit_leave_no_owned_services_or_helpers(self):
        from lifecycle import running_services, stop_services
        root = Path(__file__).resolve().parents[1]
        executable = root / 'portable/v0.5.1/LocalWhisperDictation/LocalWhisperDictation.exe'
        self.assertTrue(executable.is_file(), 'Build the current portable version first')
        powershell = Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'

        def processes():
            result = subprocess.run([str(powershell), '-NoProfile', '-Command',
                "Get-CimInstance Win32_Process -Filter \"Name='LocalWhisperDictation.exe'\" | "
                'Select-Object ProcessId,ParentProcessId,ExecutablePath,CommandLine | ConvertTo-Json -Compress'],
                capture_output=True, text=True, timeout=10, creationflags=subprocess.CREATE_NO_WINDOW)
            if result.returncode:
                raise RuntimeError('Cannot verify companion process state')
            rows = json.loads(result.stdout) if result.stdout.strip() else []
            if isinstance(rows, dict):
                rows = [rows]
            prefix = str(root / 'portable').casefold() + '\\'
            return [row for row in rows if (row.get('ExecutablePath') or '').casefold().startswith(prefix)]

        if processes():
            self.skipTest('Close the running project companion before lifecycle acceptance')

        def unrelated():
            result = subprocess.run(['docker', 'ps', '--format',
                '{{.ID}} {{.Label "com.docker.compose.project"}}'], check=True,
                capture_output=True, text=True, timeout=10, creationflags=subprocess.CREATE_NO_WINDOW)
            return {row.split()[0] for row in result.stdout.splitlines()
                    if not row.endswith(' local-whisper-dictation')}

        baseline = unrelated()
        user = ctypes.WinDLL('user32', use_last_error=True)
        user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        user.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        user.IsWindowVisible.argtypes = [wintypes.HWND]
        user.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        user.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]

        def own_window(pid):
            found = []
            @callback_type
            def visit(hwnd, unused):
                owner = wintypes.DWORD()
                user.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
                if owner.value == pid and user.IsWindowVisible(hwnd):
                    title = ctypes.create_unicode_buffer(160)
                    user.GetWindowTextW(hwnd, title, 160)
                    if title.value == 'Whisper Dictation 0.5.1':
                        found.append(hwnd)
                return True
            user.EnumWindows(visit, 0)
            return found[0] if len(found) == 1 else None

        for mode in ('normal', 'forced'):
            with self.subTest(mode=mode):
                subprocess.run(['docker', 'compose', 'up', '-d', '--wait', '--wait-timeout', '180'],
                    cwd=root, check=True, capture_output=True, text=True, timeout=200,
                    creationflags=subprocess.CREATE_NO_WINDOW)
                process = subprocess.Popen([str(executable)], cwd=root, creationflags=subprocess.CREATE_NO_WINDOW)
                try:
                    deadline = time.monotonic() + 20
                    window = None
                    while time.monotonic() < deadline and process.poll() is None:
                        window = own_window(process.pid)
                        if window:
                            break
                        time.sleep(0.1)
                    self.assertIsNotNone(window, 'Owned package window did not open')
                    helpers = [row for row in processes() if row['ParentProcessId'] == process.pid
                               and '--supervise-handle' in (row['CommandLine'] or '')]
                    self.assertEqual(len(helpers), 1, 'Exactly one lifetime helper must be present')
                    if mode == 'normal':
                        self.assertTrue(user.PostMessageW(window, 0x0010, 0, 0))
                    else:
                        process.terminate()
                    process.wait(timeout=50)
                    deadline = time.monotonic() + 25
                    while time.monotonic() < deadline:
                        if not processes() and not running_services():
                            break
                        time.sleep(0.2)
                    self.assertEqual(processes(), [], 'A dictation process/helper remained')
                    self.assertEqual(running_services(), [], 'A dictation container remained running')
                    self.assertTrue(baseline <= unrelated(), 'An unrelated container changed')
                    print(mode + ' exit: no owned processes/services; unrelated containers preserved', flush=True)
                finally:
                    if process.poll() is None:
                        process.terminate()
                        process.wait(timeout=5)
                    stop_services()
