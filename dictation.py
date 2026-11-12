"""Windows microphone and desktop bridge. Run as the ordinary signed-in user."""
import sys

# The short-lived shutdown supervisor must not import audio/UI libraries or
# create any windows while waiting for the owning companion to exit.
if __name__ == '__main__' and len(sys.argv) == 3 and sys.argv[1] == '--supervise-handle':
    from lifecycle import supervise_handle
    raise SystemExit(supervise_handle(int(sys.argv[2])))

import ctypes
from collections import deque
from ctypes import wintypes
import io
import json
import queue
import subprocess
import threading
import time
import tkinter as tk
from tkinter import ttk
import urllib.request
import wave

import sounddevice as sd
from audio_segments import AudioRouter
from transcript_quality import clean_transcript
from windows_clipboard import set_clipboard_text
from windows_input import paste_shortcut
from windows_focus import Desktop
import preferences
from lifecycle import launch_supervisor, stop_services

ENDPOINT = 'http://127.0.0.1:17863/transcribe'
RATE = 16000
VERSION = '0.5.1'


def gateway_running():
    """Both gateway and model must be running; no Docker socket is exposed to containers."""
    try:
        result = subprocess.run(['docker', 'ps', '--filter',
            'label=com.docker.compose.project=local-whisper-dictation',
            '--format', '{{.Label "com.docker.compose.service"}}'],
            capture_output=True, text=True, timeout=8,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if result.returncode != 0:
            return None  # Unknown is different from a confirmed container stop.
        return {'dictation', 'whisper'} <= set(result.stdout.splitlines())
    except (OSError, subprocess.TimeoutExpired):
        return None


def singleton(name):
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    kernel.CreateMutexW.restype = wintypes.HANDLE
    handle = kernel.CreateMutexW(None, False, 'Local\\' + name)
    if not handle or ctypes.get_last_error() == 183:
        return None
    return handle  # Retain until process exit; Windows releases it automatically.


def wav_bytes(pcm):
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(RATE)
        audio.writeframes(pcm)
    return buffer.getvalue()


class App:
    """One continuous listener and one direct-input path; no transcript widget."""
    def __init__(self):
        self.desktop = Desktop()
        self.user = self.desktop.user
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title('Whisper Dictation ' + VERSION)
        self.root.configure(bg='#171b23')
        self.root.geometry('310x96')
        self.root.resizable(False, False)
        self.root.attributes('-topmost', True)
        self.events = queue.Queue()
        self.jobs = queue.Queue(maxsize=4)
        self.audio_frames = queue.Queue(maxsize=128)
        self.pending = deque()
        self.stream = None
        self.session = 0
        self.listening = False
        self.closing = False
        self.shutdown_failed = False
        self.busy = True
        self.active_target = None
        self.note = 'Loading speech model…'
        self.saved = preferences.load()
        self.devices = [None]
        self.device_names = ['Windows default microphone']
        for index, device in enumerate(sd.query_devices()):
            if device['max_input_channels'] > 0:
                self.devices.append(index)
                self.device_names.append(f"{index}: {device['name']}")
        self.microphone = self.saved.get('microphone', self.device_names[0])
        if self.microphone not in self.device_names:
            self.microphone = self.device_names[0]
        self.model = self.saved.get('model', 'base')
        self.models = []
        self.settings_window = None
        self.canvas = tk.Canvas(self.root, width=310, height=96, bg='#171b23', highlightthickness=0,
                                cursor='hand2', takefocus=False)
        self.canvas.pack()
        self.canvas.bind('<Button-1>', self.click)
        self.menu = tk.Menu(self.root, tearoff=False, bg='#232936', fg='#eef2f8',
                            activebackground='#354052', activeforeground='white')
        self.menu.add_command(label='Microphone and speech model…', command=self.open_settings)
        self.menu.add_separator()
        self.menu.add_command(label='Quit', command=self.close)
        self.root.protocol('WM_DELETE_WINDOW', self.close)
        self.root.update_idletasks()
        self.own_window = self.desktop.toolbar(self.root)
        self.root.deiconify()
        self.draw()
        threading.Thread(target=self.hotkeys, daemon=True).start()
        threading.Thread(target=self.monitor_container, daemon=True).start()
        threading.Thread(target=self.load_models, args=(self.model,), daemon=True).start()
        threading.Thread(target=self.recognize_jobs, daemon=True).start()
        threading.Thread(target=self.process_audio, daemon=True).start()
        self.root.after(40, self.poll)

    def draw(self):
        state = (self.listening, self.note)
        if getattr(self, '_drawn', None) == state:
            return
        self._drawn = state
        c = self.canvas
        c.delete('all')
        color = '#20c779' if self.listening else '#e45461'
        c.create_oval(13, 14, 59, 60, fill=color, outline='')
        c.create_rectangle(32, 26, 40, 40, fill='#ffffff', outline='')
        c.create_oval(32, 22, 40, 30, fill='#ffffff', outline='')
        c.create_arc(26, 27, 46, 47, start=180, extent=180, style='arc', outline='#ffffff', width=2)
        c.create_line(36, 47, 36, 52, fill='white', width=2)
        c.create_line(30, 52, 42, 52, fill='white', width=2)
        c.create_text(72, 27, anchor='w', text='Listening' if self.listening else 'Off',
                      fill='#f2f5fa', font=('Segoe UI', 13, 'bold'))
        c.create_text(72, 49, anchor='w', text='Ctrl+Alt+D', fill='#a6b1c1', font=('Segoe UI', 9))
        c.create_oval(206, 24, 242, 48, fill=color if self.listening else '#3b4352', outline='')
        c.create_oval(218 if self.listening else 208, 26,
                      240 if self.listening else 230, 46, fill='white', outline='')
        c.create_text(278, 36, text='⚙', fill='#c8d2df', font=('Segoe UI Symbol', 19))
        c.create_text(13, 79, text=self.note[:49], anchor='w', fill='#a6b1c1', font=('Segoe UI', 9))

    def click(self, event):
        if event.x >= 259 and event.y < 65:
            self.menu.tk_popup(self.root.winfo_rootx() + 140, self.root.winfo_rooty() + 60)
        else:
            self.toggle()

    def hotkeys(self):
        self.user.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
        if not self.user.RegisterHotKey(None, 1, 0x4000 | 0x2 | 0x1, ord('D')):
            self.events.put(('warning', 'Ctrl+Alt+D is in use; use the toggle.'))
            return
        msg = wintypes.MSG()
        try:
            while self.user.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                if msg.message == 0x0312:
                    self.events.put(('toggle', None))
        finally:
            self.user.UnregisterHotKey(None, 1)

    def monitor_container(self):
        failures = 0
        while True:
            state = gateway_running()
            failures = failures + 1 if state is None else 0
            if state is False or failures >= 3:
                self.events.put(('container_stopped', None))
                return
            time.sleep(2)

    def load_models(self, model):
        try:
            request = urllib.request.Request(ENDPOINT.rsplit('/', 1)[0] + '/models/select',
                json.dumps({'model': model}).encode(), {'Content-Type': 'application/json'})
            with urllib.request.urlopen(request, timeout=190) as response:
                self.events.put(('models', json.load(response)))
        except Exception:
            self.events.put(('model_error', 'Model unavailable; check Docker and settings.'))

    def open_settings(self):
        if self.settings_window and self.settings_window.winfo_exists():
            self.settings_window.lift()
            return
        window = self.settings_window = tk.Toplevel(self.root)
        window.title('Dictation settings')
        window.configure(bg='#171b23')
        window.attributes('-topmost', True)
        window.resizable(False, False)
        style = ttk.Style(window)
        style.theme_use('clam')
        style.configure('Dark.TCombobox', fieldbackground='#252c39', background='#333d4c', foreground='#f2f5fa')
        tk.Label(window, text='Microphone', bg='#171b23', fg='#eef2f8').pack(anchor='w', padx=16, pady=(14, 4))
        mic = ttk.Combobox(window, values=self.device_names, state='disabled' if self.listening else 'readonly',
                           width=48, style='Dark.TCombobox')
        mic.set(self.microphone)
        mic.pack(padx=16)
        tk.Label(window, text='Speech model', bg='#171b23', fg='#eef2f8').pack(anchor='w', padx=16, pady=(12, 4))
        labels = [m['label'] for m in self.models]
        model = ttk.Combobox(window, values=labels, state='disabled' if self.listening else 'readonly',
                             width=48, style='Dark.TCombobox')
        model.set(next((m['label'] for m in self.models if m['id'] == self.model), self.model))
        model.pack(padx=16)
        tk.Label(window, text='Turn listening off before changing these settings.' if self.listening else
                 'Listening continues until you turn it off. No automatic timeout.',
                 bg='#171b23', fg='#a6b1c1').pack(padx=16, pady=12)
        def apply():
            self.microphone = mic.get()
            index = model.current()
            chosen = self.models[index]['id'] if 0 <= index < len(self.models) else self.model
            try:
                preferences.save(self.microphone, chosen)
            except OSError:
                self.note = 'Settings could not be saved.'
            window.destroy()
            self.settings_window = None
            if chosen != self.model:
                self.busy = True
                self.note = 'Loading speech model…'
                self.draw()
                threading.Thread(target=self.load_models, args=(chosen,), daemon=True).start()
        tk.Button(window, text='Save', command=apply, state='disabled' if self.listening or self.busy else 'normal',
                  bg='#303b4b', fg='white', activebackground='#42516a', activeforeground='white',
                  relief='flat', padx=20, pady=5).pack(anchor='e', padx=16, pady=(0, 14))

    def toggle(self):
        if self.closing or self.shutdown_failed:
            return
        if self.listening:
            self.stop()
            self.enqueue_audio(None, None)
            self.note = 'Off · click the switch to listen'
            self.draw()
            return
        if self.busy:
            self.note = 'Speech model is still loading.'
            self.draw()
            return
        self.session += 1
        self.pending.clear()
        self.active_target = self.desktop.destination()
        try:
            index = self.device_names.index(self.microphone)
            self.stream = sd.RawInputStream(device=self.devices[index], samplerate=RATE,
                channels=1, dtype='int16', callback=self.audio)
            self.listening = True
            self.stream.start()
            self.note = 'Speak into the active text box'
        except Exception:
            self.stop()
            self.note = 'Microphone unavailable · open settings'
        self.draw()

    def stop(self):
        self.listening = False
        if self.stream:
            stream, self.stream = self.stream, None
            stream.stop()
            stream.close()

    def audio(self, data, frames, timing, status):
        if not self.listening:
            return
        if status:
            self.events.put(('warning', 'Microphone warning · still listening'))
        target = self.active_target
        self.enqueue_audio(bytes(data) if target else b'', target)

    def enqueue_audio(self, pcm, target):
        try:
            self.audio_frames.put_nowait((self.session, target, pcm))
        except queue.Full:
            self.events.put(('warning', 'Audio queue busy · speak again'))

    def process_audio(self):
        router = AudioRouter()
        while True:
            session, target, pcm = self.audio_frames.get()
            if session != self.session:
                continue
            phrase = router.feed(session, target, pcm)
            if phrase:
                self.submit(phrase[1], phrase[0], session)

    def submit(self, pcm, target, session=None):
        try:
            self.jobs.put_nowait((self.session if session is None else session, target, pcm))
        except queue.Full:
            self.events.put(('warning', 'Speech queue busy · speak again'))

    def transcribe_pcm(self, pcm):
        request = urllib.request.Request(ENDPOINT, wav_bytes(pcm), {'Content-Type': 'audio/wav'})
        with urllib.request.urlopen(request, timeout=190) as response:
            return clean_transcript(json.load(response)['text'])

    def recognize_jobs(self):
        while True:
            session, target, pcm = self.jobs.get()
            if session != self.session:
                continue
            try:
                text = self.transcribe_pcm(pcm)
                self.events.put(('text', (session, target, text)))
            except Exception:
                self.events.put(('warning', 'Recognition failed · still listening'))

    def deliver(self, session, target, text):
        text = clean_transcript(text)
        if not text or session != self.session:
            return False
        if target is None or self.desktop.destination() != target:
            self.note = 'Destination changed · speak again'
            return False
        if self.desktop.keys_held():
            if len(self.pending) < 16:
                self.pending.append((session, target, text))
            else:
                self.note = 'Input busy · speak again'
            return False
        try:
            set_clipboard_text(self.own_window, text + ' ')
            if self.desktop.destination() != target:
                self.note = 'Destination changed · speak again'
                return False
            paste_shortcut()  # Never Enter; never selects or rewrites existing text.
            self.note = 'Listening · text sent' if self.listening else 'Off · final phrase sent'
            return True
        except OSError:
            self.note = 'Input blocked · check the active text box'
            return False

    def poll(self):
        self.active_target = self.desktop.destination()
        pending, self.pending = self.pending, deque()
        while pending:
            self.deliver(*pending.popleft())
        try:
            while True:
                event, value = self.events.get_nowait()
                if self.closing and event not in {'shutdown_done', 'shutdown_error'}:
                    continue
                if event == 'toggle':
                    self.toggle()
                elif event == 'container_stopped':
                    self.close()
                    return
                elif event == 'models':
                    self.models = value['models']
                    self.model = value['active']
                    self.busy = False
                    self.note = 'Off · click the switch to listen'
                elif event == 'model_error':
                    self.busy = False
                    self.note = value
                elif event == 'text':
                    self.deliver(*value)
                elif event == 'warning':
                    self.note = value
                elif event == 'shutdown_done':
                    self.root.destroy()
                    return
                elif event == 'shutdown_error':
                    self.closing = False
                    self.shutdown_failed = True
                    self.note = 'Could not stop services · close again to retry'
        except queue.Empty:
            pass
        self.draw()
        self.root.after(40, self.poll)

    def close(self):
        if self.closing:
            return
        try:
            self.stop()
        except Exception:
            self.listening = False
        self.session += 1
        self.pending.clear()
        self.closing = True
        self.note = 'Stopping dictation services…'
        self.draw()
        threading.Thread(target=self.shutdown, daemon=True).start()

    def shutdown(self):
        self.events.put(('shutdown_done' if stop_services() else 'shutdown_error', None))

    def run(self):
        self.root.mainloop()


if __name__ == '__main__':
    if '--watch' in sys.argv:
        raise SystemExit('Resident watcher retired. Use Start-Dictation.ps1.')
    else:
        guard = singleton('LocalWhisperDictationCompanion')
        if guard:
            try:
                supervisor = launch_supervisor(guard)
                App().run()
            except BaseException:
                stop_services()
                raise
