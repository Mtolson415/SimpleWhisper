"""Opt-in acceptance against an owned two-field WPF fixture, never a user app."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


@unittest.skipUnless(sys.platform == 'win32' and os.getenv('DICTATION_DESKTOP_TEST') == '1',
                     'Opt-in Windows synthetic background-field test')
class BackgroundAcceptance(unittest.TestCase):
    def test_locked_updates_preserve_other_field_and_restore_focus(self):
        import uiautomation as auto
        from locked_target import LockedTarget
        framework = Path(os.environ['SystemRoot']) / 'Microsoft.NET/Framework64/v4.0.30319'
        with tempfile.TemporaryDirectory(prefix='dictation-synthetic-') as folder:
            executable = Path(folder) / 'BackgroundFixture.exe'
            subprocess.run([str(framework / 'csc.exe'), '/nologo', '/target:winexe',
                '/out:' + str(executable), '/r:System.Xaml.dll',
                *['/r:' + str(framework / 'WPF' / name) for name in
                  ('PresentationFramework.dll', 'PresentationCore.dll', 'WindowsBase.dll')],
                str(Path(__file__).parent / 'fixtures/BackgroundFixture.cs')], check=True,
                capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            process = subprocess.Popen([str(executable)])
            try:
                window = auto.WindowControl(searchDepth=1, Name='Dictation background lock fixture',
                                            ProcessId=process.pid)
                self.assertTrue(window.Exists(5))
                first = window.EditControl(AutomationId='LockedField')
                second = window.EditControl(AutomationId='OtherField')
                first.SetFocus()
                target = LockedTarget.begin(auto)
                self.assertTrue(target and target.background_supported)
                second.SetFocus()
                self.assertTrue(target.write('Hello, español.'))
                self.assertEqual(first.GetValuePattern().Value, 'Synthetic prefix: Hello, español.')
                self.assertEqual(second.GetValuePattern().Value, 'Other field unchanged')
                self.assertEqual(tuple(auto.GetFocusedControl().GetRuntimeId()), tuple(second.GetRuntimeId()))
                self.assertTrue(target.write('Revised español.', revise=True))
                self.assertEqual(first.GetValuePattern().Value, 'Synthetic prefix: Revised español.')
                self.assertEqual(tuple(auto.GetFocusedControl().GetRuntimeId()), tuple(second.GetRuntimeId()))
            finally:
                process.terminate()
                process.wait(timeout=5)
