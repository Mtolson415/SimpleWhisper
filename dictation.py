"""Windows microphone and desktop bridge. Run as the ordinary signed-in user."""
import ctypes
from ctypes import wintypes
import io
import json
import queue
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk
import urllib.request
import wave

import sounddevice as sd
from audio_segments import PhraseBuffer

ENDPOINT = 'http://127.0.0.1:17863/transcribe'
RATE = 16000


def gateway_running():
    """Both gateway and model must be running; no Docker socket is exposed to containers."""
    try:
        result = subprocess.run(['docker', 'ps', '--filter',
            'label=com.docker.compose.project=local-whisper-dictation',
            '--format', '{{.Label "com.docker.compose.service"}}'],
            capture_output=True, text=True, timeout=8,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        return result.returncode == 0 and {'dictation', 'whisper'} <= set(result.stdout.splitlines())
    except (OSError, subprocess.TimeoutExpired):
        return False


def singleton(name):
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    kernel.CreateMutexW.restype = wintypes.HANDLE
    handle = kernel.CreateMutexW(None, False, 'Local\\' + name)
    if not handle or ctypes.get_last_error() == 183:
        return None
    return handle  # Retain until process exit; Windows releases it automatically.


def watch_containers():
    guard = singleton('LocalWhisperDictationWatcher')
    if not guard:
        return
    previously_running = False
    while True:
        running = gateway_running()
        if running and not previously_running and gateway_ready():
            command = [sys.executable] if getattr(sys, 'frozen', False) else [sys.executable, __file__]
            subprocess.Popen(command, creationflags=subprocess.CREATE_NO_WINDOW)
            previously_running = True
        elif not running:
            previously_running = False
        time.sleep(2)


def gateway_ready():
    try:
        with urllib.request.urlopen(ENDPOINT.rsplit('/', 1)[0] + '/health', timeout=2) as response:
            return response.status == 200
    except Exception:
        return False


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
        self.root.geometry('660x440')
        self.events = queue.Queue()
        self.stream = None
        self.busy = True  # Wait for the startup model selection before capture.
        self.chunks = []
        self.frames = 0
        self.target = None
        self.record_live = False
        self.live_paste_suppressed = False
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
        self.model_ids = []
        self.model_selector = ttk.Combobox(self.root, values=['Loading speech models…'], state='disabled', width=75)
        self.model_selector.current(0)
        self.model_selector.pack(padx=12, pady=5)
        self.model_selector.bind('<<ComboboxSelected>>', self.change_model)
        self.direct_input = tk.BooleanVar(value=True)
        ttk.Checkbutton(self.root, text='Dictate directly into active input',
                        variable=self.direct_input).pack(padx=12, pady=5)
        self.live_input = tk.BooleanVar(value=False)
        self.live_checkbox = ttk.Checkbutton(self.root, text='Live phrases — transcribe at short pauses',
                                             variable=self.live_input)
        self.live_checkbox.pack(padx=12, pady=5)
        self.preview = tk.Text(self.root, height=7, wrap='word')
        self.preview.pack(fill='both', expand=True, padx=12)
        tk.Button(self.root, text='Copy transcript', command=self.copy).pack(pady=10)
        self.root.protocol('WM_DELETE_WINDOW', self.close)
        threading.Thread(target=self.hotkeys, daemon=True).start()
        threading.Thread(target=self.monitor_container, daemon=True).start()
        threading.Thread(target=self.load_models, daemon=True).start()
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

    def monitor_container(self):
        while True:
            if not gateway_running():
                self.events.put(('container_stopped', None))
                return
            time.sleep(2)

    def load_models(self, model='base'):
        try:
            request = urllib.request.Request(ENDPOINT.rsplit('/', 1)[0] + '/models')
            if model is not None:
                request = urllib.request.Request(ENDPOINT.rsplit('/', 1)[0] + '/models/select',
                    json.dumps({'model': model}).encode(), {'Content-Type': 'application/json'})
            with urllib.request.urlopen(request, timeout=190) as response:
                self.events.put(('models', json.load(response)))
        except Exception:
            self.events.put(('error', 'Model list/change failed. Check the Docker model files.'))

    def change_model(self, event=None):
        if self.busy or self.stream:
            return
        index = self.model_selector.current()
        if not 0 <= index < len(self.model_ids):
            return
        self.busy = True
        self.status.set('Loading selected speech model…')
        self.model_selector.configure(state='disabled')
        threading.Thread(target=self.load_models, args=(self.model_ids[index],), daemon=True).start()

    def audio(self, data, frames, timing, status):
        if status:
            self.events.put(('audio_error', 'Microphone overflow. Recording discarded; try again.'))
            return
        if self.frames + frames > RATE * 120:
            self.events.put(('limit', None))
            return
        if self.record_live:
            phrase = self.segmenter.add(bytes(data))
            if phrase:
                try:
                    self.phrases.put_nowait(phrase)
                except queue.Full:
                    self.events.put(('audio_error', 'Live queue full. Use a faster model or stop-to-transcribe mode.'))
        else:
            self.chunks.append(bytes(data))
        self.frames += frames

    def toggle(self, target):
        if self.busy:
            return
        if self.stream:
            self.stop()
            self.busy = True
            if self.record_live:
                self.finish_phrases()
                self.status.set('Finishing live phrases…')
                return
            self.status.set('Transcribing locally…')
            pcm = b''.join(self.chunks)
            self.chunks.clear()
            threading.Thread(target=self.recognize, args=(pcm,), daemon=True).start()
            return
        self.target = target
        self.chunks = []
        self.frames = 0
        self.record_live = self.live_input.get()
        if self.record_live:
            self.segmenter = PhraseBuffer()
            self.phrases = queue.Queue(maxsize=8)
            self.live_paste_suppressed = False
            self.preview.delete('1.0', 'end')
            threading.Thread(target=self.recognize_phrases, daemon=True).start()
        try:
            self.stream = sd.RawInputStream(device=self.devices[self.microphone.current()],
                                            samplerate=RATE, channels=1, dtype='int16', callback=self.audio)
            self.stream.start()
            self.status.set('Live phrases — pause briefly for text; Ctrl+Alt+D stops.' if self.record_live
                            else 'Recording — Ctrl+Alt+D to stop. Maximum two minutes.')
        except Exception as error:
            self.stop()
            if self.record_live:
                self.busy = True
                self.finish_phrases()
            self.status.set('Microphone failed: ' + str(error))

    def finish_phrases(self):
        phrase = self.segmenter.flush()
        if phrase:
            try:
                self.phrases.put_nowait(phrase)
            except queue.Full:
                self.status.set('Live queue full; final phrase discarded. Review retained text.')
        try:
            self.phrases.put_nowait(None)
        except queue.Full:
            self.phrases.get_nowait()
            self.phrases.put_nowait(None)

    def recognize_phrases(self):
        phrases = self.phrases
        while True:
            pcm = phrases.get()
            if pcm is None:
                break
            try:
                self.events.put(('live_text', self.transcribe_pcm(pcm)))
            except Exception:
                self.events.put(('live_error', 'A live phrase failed. Review text; check Docker or use normal mode.'))
        self.events.put(('live_finished', None))

    def transcribe_pcm(self, pcm):
        request = urllib.request.Request(ENDPOINT, wav_bytes(pcm), {'Content-Type': 'audio/wav'})
        with urllib.request.urlopen(request, timeout=190) as response:
            return json.load(response)['text']

    def stop(self):
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None

    def recognize(self, pcm):
        try:
            text = self.transcribe_pcm(pcm)
            self.events.put(('text', text))
        except Exception:
            self.events.put(('error', 'Transcription failed. Check the Whisper container in Docker, then try again.'))

    def copy(self, text=None):
        if text is None:
            text = self.preview.get('1.0', 'end-1c')
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.root.update_idletasks()

    def insert(self, text, attempts=0, live=False):
        if live and self.live_paste_suppressed:
            return
        if not self.direct_input.get():
            if not live:
                self.busy = False
            self.status.set('Transcript ready below. Use Copy transcript to paste it yourself.')
            return
        if self.user.GetForegroundWindow() != self.target:
            if live:
                self.live_paste_suppressed = True
            else:
                self.busy = False
            self.status.set('Window changed. Transcript retained below; copy and paste when ready.')
            return
        if any(self.user.GetAsyncKeyState(key) & 0x8000 for key in (0x10, 0x11, 0x12, ord('D'))):
            if live:
                self.status.set('Phrase retained in preview while shortcut keys are held.')
                return
            if attempts < 40:
                self.root.after(50, lambda: self.insert(text, attempts + 1))
            else:
                self.busy = False
                self.status.set('Release shortcut keys. Transcript retained; use Copy transcript.')
            return
        self.copy(text)
        # Never send Enter or submit a form. Clipboard retains the transcript.
        self.user.keybd_event(0x11, 0, 0, 0)
        self.user.keybd_event(ord('V'), 0, 0, 0)
        self.user.keybd_event(ord('V'), 0, 2, 0)
        self.user.keybd_event(0x11, 0, 2, 0)
        if not live:
            self.busy = False
        self.status.set('Live phrase pasted; Ctrl+Alt+D stops recording.' if live and self.stream else
                        'Paste requested. Review text in your app. Ctrl+Alt+D for another recording.')

    def poll(self):
        try:
            while True:
                event, value = self.events.get_nowait()
                if event == 'toggle':
                    self.toggle(value)
                elif event == 'container_stopped':
                    self.close()
                    return
                elif event == 'models':
                    self.model_ids = [model['id'] for model in value['models']]
                    self.model_selector.configure(values=[model['label'] for model in value['models']])
                    self.model_selector.current(self.model_ids.index(value['active']))
                    self.busy = False
                    self.status.set('Model ready. Click a text field; Ctrl+Alt+D starts/stops.')
                elif event == 'live_text' and value:
                    prefix = ' ' if self.preview.get('1.0', 'end-1c') else ''
                    self.preview.insert('end', prefix + value)
                    self.insert(prefix + value, live=True)
                elif event == 'live_finished':
                    self.busy = False
                    self.status.set('Live recording finished. Review the transcript.')
                elif event == 'live_error':
                    self.status.set(value)
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
                    if self.record_live:
                        self.busy = True
                        self.finish_phrases()
                    self.chunks.clear()
                    self.status.set(value)
                elif event == 'error':
                    self.busy = False
                    self.status.set(value)
        except queue.Empty:
            pass
        self.model_selector.configure(state='readonly' if self.model_ids and not self.busy and not self.stream else 'disabled')
        self.live_checkbox.configure(state='disabled' if self.busy or self.stream else 'normal')
        self.root.after(50, self.poll)

    def close(self):
        self.stop()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == '__main__':
    if '--watch' in sys.argv:
        watch_containers()
    else:
        guard = singleton('LocalWhisperDictationCompanion')
        if guard:
            App().run()
