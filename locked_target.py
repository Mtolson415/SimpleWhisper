"""An in-memory destination using field APIs, without global paste keystrokes."""

LIMIT = 20000


class LockedTarget:
    def __init__(self, control, auto):
        self.control, self.auto = control, auto
        self.identity = tuple(control.GetRuntimeId())
        self.value = None
        self.failed = False
        self.background_supported = False

    @classmethod
    def begin(cls, auto=None):
        try:
            if auto is None:
                import uiautomation as auto
            control = auto.GetFocusedControl()
            if not control or control.IsPassword:
                return None
            target = cls(control, auto)
            # Only a plain editable field with an exact selection/value mapping
            # can be updated in the background. Rich documents are not rewritten.
            if control.ControlTypeName != 'EditControl':
                return target
            value = control.GetPattern(auto.PatternId.ValuePattern)
            text = control.GetPattern(auto.PatternId.TextPattern)
            if value is None or text is None or value.IsReadOnly:
                return target
            current = value.Value
            if len(current) > LIMIT:
                return target
            selection = text.GetSelection()
            if len(selection) != 1:
                return target
            before, after = text.DocumentRange.Clone(), text.DocumentRange.Clone()
            before.MoveEndpointByRange(1, selection[0], 0, waitTime=0)
            after.MoveEndpointByRange(0, selection[0], 1, waitTime=0)
            prefix, selected, suffix = (before.GetText(LIMIT + 1),
                                        selection[0].GetText(LIMIT + 1), after.GetText(LIMIT + 1))
            if prefix + selected + suffix != current:
                return target
            target.value, target.expected = value, current
            target.offset, target.end = len(prefix), len(prefix) + len(selected)
            target.last_start = None
            target.background_supported = True
            return target
        except Exception:
            return None

    def is_focused(self):
        try:
            focused = self.auto.GetFocusedControl()
            return bool(focused and tuple(focused.GetRuntimeId()) == self.identity)
        except Exception:
            return False

    def write(self, text, revise=False):
        if self.failed or not self.background_supported:
            return False
        previous = None
        try:
            previous = self.auto.GetFocusedControl()
            if (self.control.IsPassword or tuple(self.control.GetRuntimeId()) != self.identity
                    or self.value.IsReadOnly or self.value.Value != self.expected):
                self.failed = True
                return False
            start = self.last_start if revise else self.offset
            if start is None:
                return False
            updated = self.expected[:start] + text + self.expected[self.end:]
            if len(updated) > LIMIT:
                self.failed = True
                return False
            if not self.value.SetValue(updated, waitTime=0) or self.value.Value != updated:
                self.failed = True
                return False
            self.expected = updated
            self.last_start = start
            self.offset = self.end = start + len(text)
            return True
        except Exception:
            self.failed = True
            return False
        finally:
            # Some accessibility providers focus a field during SetValue even
            # though no focus was requested. Restore the user's prior control.
            if previous is not None:
                try:
                    identity = tuple(previous.GetRuntimeId())
                    focused = self.auto.GetFocusedControl()
                    if identity != self.identity and focused and tuple(focused.GetRuntimeId()) == self.identity:
                        previous.SetFocus()
                except Exception:
                    self.failed = True
