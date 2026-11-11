import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from locked_target import LockedTarget


class Range:
    def __init__(self, content, start, end):
        self.content, self.start, self.end = content, start, end

    def Clone(self):
        return Range(self.content, self.start, self.end)

    def GetText(self, limit):
        return self.content[self.start:self.end][:limit]

    def MoveEndpointByRange(self, endpoint, other, other_endpoint, waitTime=0):
        value = other.start if other_endpoint == 0 else other.end
        if endpoint == 0:
            self.start = value
        else:
            self.end = value


class LockedTargetTests(unittest.TestCase):
    def target(self):
        value = SimpleNamespace(Value='Before selected after', IsReadOnly=False)
        value.SetValue = Mock(side_effect=lambda text, **_: setattr(value, 'Value', text) or True)
        text = SimpleNamespace(DocumentRange=Range(value.Value, 0, len(value.Value)),
            GetSelection=lambda: [Range('Before selected after', 7, 15)])
        control = SimpleNamespace(IsPassword=False, ControlTypeName='EditControl', GetRuntimeId=lambda: [1, 2],
            GetPattern=lambda pattern: value if pattern == 1 else text)
        auto = SimpleNamespace(GetFocusedControl=lambda: control,
                               PatternId=SimpleNamespace(ValuePattern=1, TextPattern=2))
        return LockedTarget.begin(auto), value, control, auto

    def test_background_insertion_preserves_prefix_suffix_and_replaces_selection(self):
        target, value, _, auto = self.target()
        auto.GetFocusedControl = lambda: SimpleNamespace(GetRuntimeId=lambda: [9])
        self.assertTrue(target.write('hello'))
        self.assertEqual(value.Value, 'Before hello after')
        self.assertFalse(target.is_focused())

    def test_revisions_replace_only_last_inserted_segment(self):
        target, value, _, _ = self.target()
        self.assertTrue(target.write('draft'))
        self.assertTrue(target.write('revised draft', revise=True))
        self.assertTrue(target.write(' next phrase'))
        self.assertEqual(value.Value, 'Before revised draft next phrase after')

    def test_manual_edit_stops_updates_without_overwriting(self):
        target, value, _, _ = self.target()
        value.Value = 'User changed this'
        self.assertFalse(target.write('dictation'))
        value.SetValue.assert_not_called()
        self.assertEqual(value.Value, 'User changed this')

    def test_password_is_rejected(self):
        auto = SimpleNamespace(GetFocusedControl=lambda: SimpleNamespace(IsPassword=True))
        self.assertIsNone(LockedTarget.begin(auto))

    def test_rich_document_does_not_get_value_rewrites(self):
        _, value, control, auto = self.target()
        control.ControlTypeName = 'DocumentControl'
        target = LockedTarget.begin(auto)
        self.assertFalse(target.background_supported)
        self.assertFalse(target.write('dictation'))
        value.SetValue.assert_not_called()

    def test_read_only_field_cannot_be_updated(self):
        _, value, _, auto = self.target()
        value.IsReadOnly = True
        target = LockedTarget.begin(auto)
        self.assertFalse(target.background_supported)

    def test_changed_control_identity_cannot_be_updated(self):
        target, value, control, _ = self.target()
        control.GetRuntimeId = lambda: [99]
        self.assertFalse(target.write('dictation'))
        value.SetValue.assert_not_called()

    def test_pending_text_is_bounded(self):
        target, value, _, _ = self.target()
        self.assertFalse(target.write('x' * 20001))
        value.SetValue.assert_not_called()

    def test_provider_focus_change_restores_previously_focused_control(self):
        target, value, control, auto = self.target()
        previous = SimpleNamespace(GetRuntimeId=lambda: [9], SetFocus=Mock())
        auto.GetFocusedControl = Mock(side_effect=[previous, control])
        self.assertTrue(target.write('draft'))
        previous.SetFocus.assert_called_once_with()
