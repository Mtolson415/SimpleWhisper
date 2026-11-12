import subprocess
import sys
import unittest
from unittest.mock import Mock, patch
import lifecycle


class ShutdownTests(unittest.TestCase):
    def test_only_project_allowlisted_services_are_stopped(self):
        rows = 'aaaaaaaaaaaa dictation\nbbbbbbbbbbbb whisper\ncccccccccccc unrelated\n'
        with patch('lifecycle.subprocess.run', side_effect=[
                Mock(returncode=0, stdout=rows), Mock(returncode=0), Mock(returncode=0, stdout='')]) as run:
            self.assertTrue(lifecycle.stop_services())
        self.assertIn('label=com.docker.compose.project=local-whisper-dictation', run.call_args_list[0].args[0])
        self.assertEqual(run.call_args_list[1].args[0],
                         ['docker', 'stop', '--timeout', '10', 'aaaaaaaaaaaa', 'bbbbbbbbbbbb'])

    def test_stopped_state_is_verified_not_assumed(self):
        with patch('lifecycle.subprocess.run', side_effect=[
                Mock(returncode=0, stdout='aaaaaaaaaaaa whisper'), Mock(returncode=0),
                Mock(returncode=0, stdout='aaaaaaaaaaaa whisper')]):
            self.assertFalse(lifecycle.stop_services())

    def test_already_stopped_is_safe_and_idempotent(self):
        with patch('lifecycle.subprocess.run', return_value=Mock(returncode=0, stdout='')) as run:
            self.assertTrue(lifecycle.stop_services())
        self.assertTrue(all(call.args[0][1] == 'ps' for call in run.call_args_list))

    def test_invalid_container_identifiers_are_not_used(self):
        with patch('lifecycle.subprocess.run', return_value=Mock(returncode=0, stdout='--all whisper')) as run:
            self.assertEqual(lifecycle.running_services(), [])

    def test_docker_failure_is_reported(self):
        with patch('lifecycle.subprocess.run', return_value=Mock(returncode=1, stdout='')):
            self.assertFalse(lifecycle.stop_services())

    def test_timeout_is_reported(self):
        with patch('lifecycle.subprocess.run', side_effect=subprocess.TimeoutExpired('docker', 8)):
            self.assertFalse(lifecycle.stop_services())


@unittest.skipUnless(sys.platform == 'win32', 'Windows process lifetime')
class SupervisorTests(unittest.TestCase):
    def test_supervisor_stops_services_after_owner_handle_signals_and_exits(self):
        kernel = Mock()
        kernel.WaitForSingleObject.return_value = 0
        with patch('lifecycle.kernel_api', return_value=kernel), patch('lifecycle.stop_services', return_value=True) as stop:
            self.assertEqual(lifecycle.supervise_handle(123), 0)
        kernel.WaitForSingleObject.assert_called_once_with(123, 0xFFFFFFFF)
        kernel.CloseHandle.assert_called_once_with(123)
        stop.assert_called_once_with()

    def test_invalid_owner_handle_does_not_stop_unrelated_running_app(self):
        kernel = Mock()
        kernel.WaitForSingleObject.return_value = 0xFFFFFFFF
        with patch('lifecycle.kernel_api', return_value=kernel), patch('lifecycle.stop_services') as stop:
            self.assertEqual(lifecycle.supervise_handle(123), 1)
        stop.assert_not_called()
        kernel.CloseHandle.assert_called_once_with(123)

    def test_launcher_inherits_wait_only_handle_and_never_waits_for_its_child(self):
        kernel = Mock()
        kernel.OpenProcess.return_value = 123
        with patch('lifecycle.kernel_api', return_value=kernel), patch('lifecycle.subprocess.Popen') as popen:
            lifecycle.launch_supervisor()
        self.assertEqual(kernel.OpenProcess.call_args.args[:2], (0x00100000, True))
        command = popen.call_args.args[0]
        self.assertEqual(command[-2:], ['--supervise-handle', '123'])
        self.assertEqual(popen.call_args.kwargs['startupinfo'].lpAttributeList, {'handle_list': [123]})
        self.assertTrue(popen.call_args.kwargs['close_fds'])
        kernel.CloseHandle.assert_called_once_with(123)

    def test_companion_guard_remains_alive_in_supervisor_until_cleanup_finishes(self):
        kernel = Mock()
        kernel.OpenProcess.return_value = 123
        kernel.SetHandleInformation.return_value = True
        with patch('lifecycle.kernel_api', return_value=kernel), patch('lifecycle.subprocess.Popen') as popen:
            lifecycle.launch_supervisor(456)
        self.assertEqual(popen.call_args.kwargs['startupinfo'].lpAttributeList, {'handle_list': [123, 456]})
        self.assertEqual([call.args for call in kernel.SetHandleInformation.call_args_list],
                         [(456, 1, 1), (456, 1, 0)])
