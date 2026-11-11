"""Immediate Unicode clipboard writes; avoids Tk delayed rendering with UIA."""
import ctypes
from ctypes import wintypes
import time


def set_clipboard_text(owner, text):
    user = ctypes.WinDLL('user32', use_last_error=True)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    user.OpenClipboard.argtypes = [wintypes.HWND]
    user.OpenClipboard.restype = wintypes.BOOL
    user.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
    user.SetClipboardData.restype = wintypes.HANDLE
    kernel.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    kernel.GlobalAlloc.restype = wintypes.HANDLE
    kernel.GlobalLock.argtypes = [wintypes.HANDLE]
    kernel.GlobalLock.restype = ctypes.c_void_p
    kernel.GlobalUnlock.argtypes = [wintypes.HANDLE]
    kernel.GlobalFree.argtypes = [wintypes.HANDLE]
    payload = (text + '\0').encode('utf-16-le')
    memory = kernel.GlobalAlloc(0x0002, len(payload))
    if not memory:
        raise OSError('Could not allocate clipboard text')
    transferred = False
    opened = False
    try:
        address = kernel.GlobalLock(memory)
        if not address:
            raise OSError('Could not access clipboard memory')
        ctypes.memmove(address, payload, len(payload))
        kernel.GlobalUnlock(memory)
        for _ in range(5):
            opened = bool(user.OpenClipboard(owner))
            if opened:
                break
            time.sleep(0.01)
        if not opened:
            raise OSError('Clipboard is busy')
        if not user.EmptyClipboard() or not user.SetClipboardData(13, memory):
            raise OSError('Windows could not set clipboard text')
        transferred = True
    finally:
        if opened:
            user.CloseClipboard()
        if not transferred:
            kernel.GlobalFree(memory)
