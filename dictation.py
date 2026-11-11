"""Windows microphone and desktop bridge. Run as the ordinary signed-in user."""
import ctypes
from ctypes import wintypes
import io
import json
import queue
import threading
import tkinter as tk
from tkinter import ttk
import urllib.request
import wave

import sounddevice as sd

ENDPOINT = 'http://127.0.0.1:17863/transcribe'
RATE = 16000


def wav_bytes(pcm):
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(RATE)
        audio.writeframes(pcm)
    return buffer.getvalue()


class App:
    def __init__(self):
        self.user = ctypes.WinDLL('user32', use_last_error=True)
        self.user.GetForegroundWindow.restype = wintypes.HWND
        self.user.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
        self.root = tk.Tk()
        self.root.title('Local Whisper Dictation')
        self.root.geometry('620x320')
        self.events = queue.Queue()
        self.stream = None
        self.busy = False
        self.chunks = []
        self.frames = 0
        self.target = None
        self.status = tk.StringVar(value='Click a text field in another app. Ctrl+Alt+D starts/stops.')
        tk.Label(self.root, textvariable=self.status, wraplength=500).pack(pady=12)
        self.devices = [None]
        names = ['Windows default microphone']
        for index, device in enumerate(sd.query_devices()):
            if device['max_input_channels'] > 0:
                self.devices.append(index)
                names.append(f"{index}: {device['name']}")
        self.microphone = ttk.Combobox(self.root, values=names, state='readonly', width=75)
        self.microphone.current(0)
        self.microphone.pack(padx=12, pady=5)
        self.preview = tk.Text(self.root, height=7, wrap='word')
        self.preview.pack(fill='both', expand=True, padx=12)
        tk.Button(self.root, text='Copy transcript', command=self.copy).pack(pady=10)
        self.root.protocol('WM_DELETE_WINDOW', self.close)
        threading.Thread(target=self.hotkeys, daemon=True).start()
        self.root.after(50, self.poll)

    def hotkeys(self):
        # Register only the shortcut, without installing a keyboard logging hook.
        if not self.user.RegisterHotKey(None, 1, 0x4000 | 0x2 | 0x1, ord('D')):
            self.events.put(('error', 'Ctrl+Alt+D is in use. Close the other dictation instance.'))
            return
        msg = wintypes.MSG()
        try:
            while self.user.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                if msg.message == 0x0312:
                    self.events.put(('toggle', self.user.GetForegroundWindow()))
        finally:
            self.user.UnregisterHotKey(None, 1)

    def audio(self, data, frames, timing, status):
        if status:
            self.events.put(('audio_error', 'Microphone overflow. Recording discarded; try again.'))
            return
        if self.frames + frames > RATE * 120:
            self.events.put(('limit', None))
            return
        self.chunks.append(bytes(data))
        self.frames += frames

    def toggle(self, target):
        if self.busy:
            return
        if self.stream:
            self.stop()
            self.busy = True
            self.status.set('Transcribing locally…')
            pcm = b''.join(self.chunks)
            self.chunks.clear()
            threading.Thread(target=self.recognize, args=(pcm,), daemon=True).start()
            return
        self.target = target
        self.chunks = []
        self.frames = 0
        try:
            self.stream = sd.RawInputStream(device=self.devices[self.microphone.current()],
                                            samplerate=RATE, channels=1, dtype='int16', callback=self.audio)
            self.stream.start()
            self.status.set('Recording — Ctrl+Alt+D to stop. Maximum two minutes.')
        except Exception as error:
            self.stop()
            self.status.set('Microphone failed: ' + str(error))

    def stop(self):
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None

    def recognize(self, pcm):
        try:
            request = urllib.request.Request(ENDPOINT, wav_bytes(pcm), {'Content-Type': 'audio/wav'})
            with urllib.request.urlopen(request, timeout=190) as response:
                text = json.load(response)['text']
            self.events.put(('text', text))
        except Exception:
            self.events.put(('error', 'Transcription failed. Check Docker and Lemonade, then try again.'))

    def copy(self):
        text = self.preview.get('1.0', 'end-1c')
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.root.update_idletasks()

    def insert(self, text, attempts=0):
        if self.user.GetForegroundWindow() != self.target:
            self.busy = False
            self.status.set('Window changed. Transcript retained below; copy and paste when ready.')
            return
        if any(self.user.GetAsyncKeyState(key) & 0x8000 for key in (0x10, 0x11, 0x12, ord('D'))):
            if attempts < 40:
                self.root.after(50, lambda: self.insert(text, attempts + 1))
            else:
                self.busy = False
                self.status.set('Release shortcut keys. Transcript retained; use Copy transcript.')
            return
        self.copy()
        # Never send Enter or submit a form. Clipboard retains the transcript.
        self.user.keybd_event(0x11, 0, 0, 0)
        self.user.keybd_event(ord('V'), 0, 0, 0)
        self.user.keybd_event(ord('V'), 0, 2, 0)
        self.user.keybd_event(0x11, 0, 2, 0)
        self.busy = False
        self.status.set('Paste requested. Review text in your app. Ctrl+Alt+D for another recording.')

    def poll(self):
        try:
            while True:
                event, value = self.events.get_nowait()
                if event == 'toggle':
                    self.toggle(value)
                elif event == 'text':
                    self.preview.delete('1.0', 'end')
                    self.preview.insert('1.0', value)
                    if value:
                        self.insert(value)
                    else:
                        self.busy = False
                        self.status.set('No speech detected. Try again.')
                elif event == 'limit' and self.stream:
                    self.toggle(self.target)
                elif event == 'audio_error' and self.stream:
                    self.stop()
                    self.chunks.clear()
                    self.status.set(value)
                elif event == 'error':
                    self.busy = False
                    self.status.set(value)
        except queue.Empty:
            pass
        self.root.after(50, self.poll)

    def close(self):
        self.stop()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == '__main__':
    App().run()
