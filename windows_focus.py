"""Small native focus bridge. No accessibility provider or text reads required."""
import ctypes
from ctypes import wintypes
import os


class GUIThreadInfo(ctypes.Structure):
    _fields_ = [('cbSize', wintypes.DWORD), ('flags', wintypes.DWORD),
                *[(name, wintypes.HWND) for name in
                  ('active', 'focus', 'capture', 'menu', 'move', 'caret')],
                ('caret_rect', wintypes.RECT)]


class Desktop:
    def __init__(self):
        self.user = ctypes.WinDLL('user32', use_last_error=True)
        self.user.GetForegroundWindow.restype = wintypes.HWND
        self.user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        self.user.GetWindowThreadProcessId.restype = wintypes.DWORD
        self.user.GetGUIThreadInfo.argtypes = [wintypes.DWORD, ctypes.POINTER(GUIThreadInfo)]
        self.user.GetGUIThreadInfo.restype = wintypes.BOOL
        self.user.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
        self.user.GetAncestor.restype = wintypes.HWND
        self.get_style = self.user.GetWindowLongPtrW if ctypes.sizeof(ctypes.c_void_p) == 8 else self.user.GetWindowLongW
        self.set_style = self.user.SetWindowLongPtrW if ctypes.sizeof(ctypes.c_void_p) == 8 else self.user.SetWindowLongW
        self.get_style.argtypes = [wintypes.HWND, ctypes.c_int]
        self.get_style.restype = ctypes.c_ssize_t
        self.set_style.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
        self.set_style.restype = ctypes.c_ssize_t
        self.user.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND,
            ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT]
        self.pid = os.getpid()

    def destination(self):
        window = self.user.GetForegroundWindow()
        if not window:
            return None
        pid = wintypes.DWORD()
        thread = self.user.GetWindowThreadProcessId(window, ctypes.byref(pid))
        if not thread or pid.value == self.pid:
            return None  # Includes the toolbar, its menu, and every settings field.
        info = GUIThreadInfo(cbSize=ctypes.sizeof(GUIThreadInfo))
        if (not self.user.GetGUIThreadInfo(thread, ctypes.byref(info)) or not info.focus
                or info.flags & 0x1E or self.user.GetForegroundWindow() != window):
            return None
        return (window, info.focus)

    def keys_held(self):
        return any(self.user.GetAsyncKeyState(key) & 0x8000
                   for key in (0x01, 0x02, 0x10, 0x11, 0x12, 0x5B, 0x5C))

    def toolbar(self, widget):
        window = self.user.GetAncestor(widget.winfo_id(), 2)
        # NOACTIVATE keeps the text caret in the user's app on a toolbar click.
        style = self.get_style(window, -20) | 0x08000000 | 0x00000080
        self.set_style(window, -20, style)
        self.user.SetWindowPos(window, wintypes.HWND(-1), 0, 0, 0, 0, 0x33)
        try:
            dark = wintypes.BOOL(True)
            dwm = ctypes.WinDLL('dwmapi')
            dwm.DwmSetWindowAttribute.argtypes = [wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]
            dwm.DwmSetWindowAttribute(window, 20, ctypes.byref(dark), ctypes.sizeof(dark))
        except OSError:
            pass
        return window
