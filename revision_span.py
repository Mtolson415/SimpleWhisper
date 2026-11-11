"""Capability-gated revisions of only the last span inserted by this app.

No whole-document reads, forced focus, arbitrary backspacing or protected-field input.
UI Automation calls belong to the companion's GUI thread.
"""


def compare_endpoints(left, endpoint, right, other_endpoint):
    # uiautomation 2.0.29's convenience wrapper passes the wrapper object to COM
    # for this method. Use the documented native interface with native ranges.
    native = getattr(left, 'textRange', None)
    if native is not None:
        return native.CompareEndpoints(endpoint, right.textRange, other_endpoint)
    return left.CompareEndpoints(endpoint, right, other_endpoint)


class RevisionSpan:
    def __init__(self, auto, control, pattern, origin):
        self.auto = auto
        self.identity = tuple(control.GetRuntimeId())
        self.pattern = pattern
        self.origin = origin
        self.range = None
        self.expected = ''

    @classmethod
    def begin(cls, auto=None):
        try:
            if auto is None:
                import uiautomation as auto
            control = auto.GetFocusedControl()
            if not control or control.IsPassword:
                return None
            pattern = control.GetPattern(auto.PatternId.TextPattern)
            if not pattern:
                return None
            selections = pattern.GetSelection()
            if len(selections) != 1 or compare_endpoints(selections[0], 0, selections[0], 1) != 0:
                return None
            return cls(auto, control, pattern, selections[0].Clone())
        except Exception:
            return None

    def _caret(self):
        control = self.auto.GetFocusedControl()
        if not control or control.IsPassword or tuple(control.GetRuntimeId()) != self.identity:
            return None
        selections = self.pattern.GetSelection()
        if len(selections) != 1 or compare_endpoints(selections[0], 0, selections[0], 1) != 0:
            return None
        return selections[0]

    def record(self, text):
        try:
            caret = self._caret()
            if caret is None:
                return False
            candidate = caret.Clone()
            candidate.MoveEndpointByUnit(0, self.auto.TextUnit.Character, -len(text), waitTime=0)
            if candidate.GetText(len(text) + 2) != text:
                return False
            # Providers may keep a collapsed bookmark before or after inserted text.
            if (compare_endpoints(candidate, 0, self.origin, 0) != 0 and
                    compare_endpoints(candidate, 1, self.origin, 1) != 0):
                return False
            self.range = candidate
            self.expected = text
            return True
        except Exception:
            return False

    def prepare_revision(self):
        try:
            if self.range is None:
                return False
            caret = self._caret()
            if caret is None or compare_endpoints(caret, 0, self.range, 1) != 0:
                return False
            if self.range.GetText(len(self.expected) + 2) != self.expected:
                return False
            self.origin = self.range.Clone()
            self.range.Select(waitTime=0)
            selected = self.pattern.GetSelection()
            if len(selected) != 1 or selected[0].GetText(len(self.expected) + 2) != self.expected:
                return False
            if (compare_endpoints(selected[0], 0, self.range, 0) != 0 or
                    compare_endpoints(selected[0], 1, self.range, 1) != 0):
                return False
            return True
        except Exception:
            return False
