"""Checked, pointer-size-correct Windows keyboard input for clipboard pastes."""
import ctypes
from ctypes import wintypes


class KeyboardInput(ctypes.Structure):
    _fields_ = [('vk', wintypes.WORD), ('scan', wintypes.WORD),
                ('flags', wintypes.DWORD), ('time', wintypes.DWORD),
                ('extra', ctypes.c_size_t)]


class MouseInput(ctypes.Structure):
    _fields_ = [('x', wintypes.LONG), ('y', wintypes.LONG),
                ('data', wintypes.DWORD), ('flags', wintypes.DWORD),
                ('time', wintypes.DWORD), ('extra', ctypes.c_size_t)]


class InputData(ctypes.Union):
    _fields_ = [('keyboard', KeyboardInput), ('mouse', MouseInput)]


class Input(ctypes.Structure):
    _fields_ = [('type', wintypes.DWORD), ('data', InputData)]


def paste_shortcut():
    user = ctypes.WinDLL('user32', use_last_error=True)
    user.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(Input), ctypes.c_int]
    user.SendInput.restype = wintypes.UINT
    keys = [(0x11, 0), (ord('V'), 0), (ord('V'), 2), (0x11, 2)]
    inputs = (Input * len(keys))(*[
        Input(type=1, data=InputData(keyboard=KeyboardInput(vk=key, flags=flags)))
        for key, flags in keys])
    if user.SendInput(len(inputs), inputs, ctypes.sizeof(Input)) != len(inputs):
        # Release modifiers even if Windows accepted only part of the batch.
        releases = (Input * 2)(*[
            Input(type=1, data=InputData(keyboard=KeyboardInput(vk=key, flags=2)))
            for key in (ord('V'), 0x11)])
        user.SendInput(2, releases, ctypes.sizeof(Input))
        raise OSError('Windows blocked keyboard input')
