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
    def setUp(self):
        patcher = patch('dictation.paste_shortcut')
        self.paste = patcher.start()
        self.addCleanup(patcher.stop)

    def app(self):
        app = App.__new__(App)
        app.target = 123
        app.stream = None
        app.pending_pastes = []
        app.record_locked = True
        app.locked_target = Mock(background_supported=False)
        app.locked_target.is_focused.return_value = True
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

    def test_marker_only_text_never_reaches_clipboard_or_keyboard(self):
        app = self.app()
        app.insert('[BLANK_AUDIO]')
        app.copy.assert_not_called()
        app.user.keybd_event.assert_not_called()

    def test_continuous_session_does_not_stop_at_two_minutes(self):
        app = self.app()
        app.events = queue.Queue()
        app.frames = 16000 * 121
        app.record_continuous = True
        app.session_limit_seconds = None
        app.record_live = True
        app.record_rolling = False
        app.segmenter = Mock()
        app.segmenter.add.return_value = None
        app.audio(b'\0\0' * 1600, 1600, None, False)
        self.assertTrue(app.events.empty())
        self.assertEqual(app.frames, 16000 * 121 + 1600)

    def test_selected_auto_stop_limit_is_honored(self):
        app = self.app()
        app.events = queue.Queue()
        app.frames = 16000 * 300
        app.record_continuous = True
        app.session_limit_seconds = 300
        app.audio(b'\0\0' * 1600, 1600, None, False)
        self.assertEqual(app.events.get_nowait(), ('limit', None))

    def test_microphone_warning_does_not_stop_capture(self):
        app = self.app()
        app.events = queue.Queue()
        app.frames = 0
        app.record_continuous = True
        app.session_limit_seconds = None
        app.record_live = False
        app.chunks = []
        app.audio(b'\0\0' * 1600, 1600, None, True)
        self.assertEqual(app.events.get_nowait()[0], 'audio_warning')
        self.assertEqual(app.frames, 1600)

    def test_temporary_docker_status_failures_do_not_close_companion(self):
        app = self.app()
        app.events = queue.Queue()
        with patch('dictation.gateway_running', side_effect=[None, None, True, False]), patch('dictation.time.sleep'):
            app.monitor_container()
        self.assertEqual(app.events.qsize(), 1)
        self.assertEqual(app.events.get_nowait(), ('container_stopped', None))

    def test_full_phrase_queue_warns_and_keeps_recording(self):
        app = self.app()
        app.events = queue.Queue()
        app.frames = 0
        app.record_continuous = True
        app.session_limit_seconds = None
        app.record_live = True
        app.record_rolling = False
        app.segmenter = Mock()
        app.segmenter.add.return_value = b'new phrase'
        app.phrases = queue.Queue(maxsize=1)
        app.phrases.put(b'old phrase')
        app.audio(b'\0\0' * 1600, 1600, None, False)
        self.assertEqual(app.events.get_nowait()[0], 'audio_warning')
        self.assertEqual(app.phrases.get_nowait(), b'new phrase')
        self.assertEqual(app.frames, 1600)

    def test_three_docker_status_failures_close_companion(self):
        app = self.app()
        app.events = queue.Queue()
        with patch('dictation.gateway_running', side_effect=[None, None, None]), patch('dictation.time.sleep'):
            app.monitor_container()
        self.assertEqual(app.events.get_nowait(), ('container_stopped', None))

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
        self.paste.assert_called_once_with()
        self.assertFalse(app.busy)

    def test_live_paste_copies_only_new_phrase_and_keeps_busy_state(self):
        app = self.app()
        app.live_paste_suppressed = False
        app.stream = Mock()
        app.insert(' new phrase', live=True)
        app.copy.assert_called_once_with(' new phrase')
        self.assertTrue(app.busy)

    def test_live_window_switch_pauses_then_resumes_in_original_window(self):
        app = self.app()
        app.live_paste_suppressed = False
        app.user.GetForegroundWindow.return_value = 456
        app.insert('first phrase', live=True)
        app.copy.assert_not_called()
        self.paste.assert_not_called()
        app.user.GetForegroundWindow.return_value = 123
        app.insert('later phrase', live=True)
        app.copy.assert_called_once_with('later phrase')
        self.paste.assert_called_once()
        self.assertFalse(app.live_paste_suppressed)

    def test_start_from_companion_requests_destination_without_opening_microphone(self):
        app = self.app()
        app.busy = False
        app.user.GetAncestor.return_value = 123
        with patch('dictation.sd.RawInputStream') as microphone:
            app.toggle(123)
        microphone.assert_not_called()
        self.assertIn('destination text box first', app.status.set.call_args.args[0])

    def test_revision_safety_stop_remains_latched(self):
        app = self.app()
        app.live_paste_suppressed = True
        app.insert('Later phrase', live=True)
        self.paste.assert_not_called()

    def test_locked_background_update_never_sends_global_keys_or_clipboard(self):
        app = self.app()
        app.live_paste_suppressed = False
        app.locked_target = Mock(background_supported=True)
        app.locked_target.write.return_value = True
        app.user.GetForegroundWindow.return_value = 456
        self.assertTrue(app.insert('Synthetic phrase', live=True))
        app.locked_target.write.assert_called_once_with('Synthetic phrase', revise=False)
        self.paste.assert_not_called()
        app.copy.assert_not_called()

    def test_unlocked_mode_follows_current_window(self):
        app = self.app()
        app.record_locked = False
        app.live_paste_suppressed = False
        app.user.GetForegroundWindow.return_value = 456
        self.assertTrue(app.insert('Synthetic phrase', live=True))
        self.assertEqual(app.target, 456)
        self.paste.assert_called_once()

    def test_locked_unsupported_field_never_redirects_to_other_field(self):
        app = self.app()
        app.live_paste_suppressed = False
        app.locked_target.is_focused.return_value = False
        self.assertFalse(app.insert('Synthetic phrase', live=True))
        self.paste.assert_not_called()
        app.copy.assert_not_called()

    def test_rolling_focus_change_skips_disrupted_phrase_then_resumes_next(self):
        app = self.app()
        app.live_paste_suppressed = False
        app.draft_phrase = None
        app.completed_text = ''
        app.preview = Mock()
        app.user.GetForegroundWindow.return_value = 456
        app.render_draft(1, 'First draft', False)
        app.user.GetForegroundWindow.return_value = 123
        app.render_draft(1, 'First phrase', True)
        self.paste.assert_not_called()
        with patch('dictation.RevisionSpan.begin', return_value=None):
            app.render_draft(2, 'Second phrase', True)
        app.copy.assert_called_once_with(' Second phrase')
        self.assertFalse(app.live_paste_suppressed)

    def test_focus_change_before_draft_verification_does_not_latch_edit_stop(self):
        app = self.app()
        app.live_paste_suppressed = False
        app.user.GetForegroundWindow.return_value = 456
        span = Mock()
        app.remember_draft(span, 'Synthetic draft', False)
        span.record.assert_not_called()
        self.assertTrue(app.draft_abandoned)
        self.assertFalse(app.live_paste_suppressed)

    def test_live_held_shortcut_queues_then_pastes_in_order(self):
        app = self.app()
        app.live_paste_suppressed = False
        app.stream = Mock()
        app.user.GetAsyncKeyState.return_value = 0x8000
        app.insert('First', live=True)
        app.insert(' second', live=True)
        app.copy.assert_not_called()
        app.user.GetAsyncKeyState.return_value = 0
        app.flush_pastes()
        app.copy.assert_called_once_with('First second')
        self.paste.assert_called_once()
        self.assertEqual(app.pending_pastes, [])

    def test_pending_phrase_is_cancelled_after_focus_change(self):
        app = self.app()
        app.live_paste_suppressed = False
        app.pending_pastes = ['Synthetic phrase']
        app.user.GetForegroundWindow.return_value = 456
        app.flush_pastes()
        self.paste.assert_not_called()
        self.assertEqual(app.pending_pastes, [])
        self.assertFalse(app.live_paste_suppressed)

    def test_blocked_input_is_reported(self):
        app = self.app()
        self.paste.side_effect = OSError('blocked')
        self.assertFalse(app.insert('Synthetic phrase'))
        self.assertIn('blocked paste', app.status.set.call_args.args[0])
        self.assertFalse(app.busy)

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
