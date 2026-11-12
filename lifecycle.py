"""Stop only this project's speech services; supervise the companion's lifetime."""
import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import re
import subprocess
import sys

PROJECT = 'local-whisper-dictation'
SERVICES = {'dictation', 'whisper'}


def running_services():
    result = subprocess.run(['docker', 'ps', '--filter',
        'label=com.docker.compose.project=' + PROJECT, '--format',
        '{{.ID}} {{.Label "com.docker.compose.service"}}'],
        capture_output=True, text=True, timeout=8,
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if result.returncode:
        raise OSError('Cannot inspect dictation services')
    found = []
    for line in result.stdout.splitlines():
        fields = line.split()
        if len(fields) == 2 and fields[1] in SERVICES and re.fullmatch(r'[a-f0-9]{12,64}', fields[0]):
            found.append(fields[0])
    return found


def stop_services():
    try:
        owned = running_services()
        if owned:
            result = subprocess.run(['docker', 'stop', '--timeout', '10', *owned],
                capture_output=True, text=True, timeout=30,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            if result.returncode:
                return False
        return not running_services()
    except (OSError, subprocess.TimeoutExpired):
        return False


def kernel_api():
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.SetHandleInformation.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD]
    kernel.SetHandleInformation.restype = wintypes.BOOL
    return kernel


def launch_supervisor(companion_guard=None):
    kernel = kernel_api()
    # An inherited process handle avoids PID-reuse/startup races. The helper
    # can only wait for this process; no termination privilege is requested.
    handle = kernel.OpenProcess(0x00100000, True, os.getpid())
    if not handle:
        raise OSError('Cannot supervise dictation lifetime')
    try:
        startup = subprocess.STARTUPINFO()
        handles = [handle]
        if companion_guard is not None:
            if not kernel.SetHandleInformation(companion_guard, 1, 1):
                raise OSError('Cannot preserve shutdown ownership')
            handles.append(companion_guard)
        startup.lpAttributeList = {'handle_list': handles}
        command = [sys.executable]
        if not getattr(sys, 'frozen', False):
            command.append(str(Path(__file__).with_name('dictation.py')))
        command += ['--supervise-handle', str(handle)]
        return subprocess.Popen(command, startupinfo=startup, close_fds=True,
                                creationflags=subprocess.CREATE_NO_WINDOW)
    finally:
        if companion_guard is not None:
            kernel.SetHandleInformation(companion_guard, 1, 0)
        kernel.CloseHandle(handle)


def supervise_handle(handle):
    kernel = kernel_api()
    try:
        completed = kernel.WaitForSingleObject(handle, 0xFFFFFFFF) == 0
    finally:
        kernel.CloseHandle(handle)
    return 0 if completed and stop_services() else 1
