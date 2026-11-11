import unittest
from unittest.mock import Mock
from types import SimpleNamespace
from revision_span import RevisionSpan, compare_endpoints


class Range:
    def __init__(self, state, start, end):
        self.state, self.start, self.end = state, start, end

    def Clone(self):
        return Range(self.state, self.start, self.end)

    def CompareEndpoints(self, endpoint, other, other_endpoint):
        return (self.start if endpoint == 0 else self.end) - (other.start if other_endpoint == 0 else other.end)

    def MoveEndpointByUnit(self, endpoint, unit, count, waitTime=0):
        self.start += count

    def GetText(self, maximum=-1):
        return self.state.text[self.start:self.end]

    def Select(self, waitTime=0):
        self.state.selected = True
        self.state.selection = self.Clone()


class RevisionTests(unittest.TestCase):
    def test_native_compare_receives_native_com_range(self):
        left, right = SimpleNamespace(textRange=Mock()), SimpleNamespace(textRange=Mock())
        compare_endpoints(left, 0, right, 1)
        left.textRange.CompareEndpoints.assert_called_once_with(0, right.textRange, 1)

    def test_field_without_text_pattern_is_rejected(self):
        control = SimpleNamespace(IsPassword=False, GetPattern=lambda _: None)
        auto = SimpleNamespace(GetFocusedControl=lambda: control, PatternId=SimpleNamespace(TextPattern=1))
        self.assertIsNone(RevisionSpan.begin(auto))
    def setup_span(self):
        state = SimpleNamespace(text='user: ', caret=6, selected=False)
        pattern = SimpleNamespace(GetSelection=lambda: [state.selection] if state.selected else [Range(state, state.caret, state.caret)])
        control = SimpleNamespace(IsPassword=False, GetRuntimeId=lambda: [1], GetPattern=lambda _: pattern)
        auto = SimpleNamespace(GetFocusedControl=lambda: control, PatternId=SimpleNamespace(TextPattern=1),
                               TextUnit=SimpleNamespace(Character=0))
        span = RevisionSpan.begin(auto)
        state.text += 'hello'
        state.caret += 5
        self.assertTrue(span.record('hello'))
        return state, span, auto

    def test_only_verified_inserted_span_is_selected(self):
        state, span, _ = self.setup_span()
        self.assertTrue(span.prepare_revision())
        self.assertTrue(state.selected)
        self.assertEqual((span.range.start, span.range.end), (6, 11))

    def test_caret_movement_prevents_selection(self):
        state, span, _ = self.setup_span()
        state.caret = 2
        self.assertFalse(span.prepare_revision())
        self.assertFalse(state.selected)

    def test_user_edit_prevents_selection(self):
        state, span, _ = self.setup_span()
        state.text = 'user: jello'
        self.assertFalse(span.prepare_revision())
        self.assertFalse(state.selected)

    def test_focus_change_prevents_selection(self):
        state, span, auto = self.setup_span()
        auto.GetFocusedControl = lambda: None
        self.assertFalse(span.prepare_revision())
        self.assertFalse(state.selected)

    def test_password_field_is_rejected(self):
        auto = SimpleNamespace(GetFocusedControl=lambda: SimpleNamespace(IsPassword=True))
        self.assertIsNone(RevisionSpan.begin(auto))
