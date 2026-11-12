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
VERSION = '0.5.2'


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
        self.root.title('SimpleWhisper')
        self.root.configure(bg='#171b23')
        self.root.geometry('310x96')
        self.root.resizable(False, False)
        self.root.attributes('-topmost', True)
        self.always_on_top = True
        self.hotkey_updates = queue.Queue()
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
        self.shortcut = self.saved.get('shortcut', preferences.DEFAULT_SHORTCUT)
        self.hotkey_updates.put(self.shortcut)
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
        self.menu.add_command(label='Settings…', command=self.open_settings)
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
        state = (self.listening, self.note, self.always_on_top, self.shortcut)
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
        c.create_text(72, 49, anchor='w', text=self.shortcut, fill='#c5cfdd', font=('Segoe UI', 9))
        c.create_oval(206, 24, 242, 48, fill='#20a779' if self.always_on_top else '#3b4352', outline='')
        c.create_oval(218 if self.always_on_top else 208, 26,
                      240 if self.always_on_top else 230, 46, fill='white', outline='')
        c.create_text(224, 11, text='On top', fill='#c5cfdd', font=('Segoe UI', 8))
        c.create_text(278, 36, text='⚙', fill='#c8d2df', font=('Segoe UI Symbol', 19))
        c.create_text(13, 79, text=self.note[:49], anchor='w', fill='#a6b1c1', font=('Segoe UI', 9))

    def click(self, event):
        if event.x >= 259 and event.y < 65:
            self.menu.tk_popup(self.root.winfo_rootx() + 140, self.root.winfo_rooty() + 60)
        elif 198 <= event.x <= 250 and 20 <= event.y <= 57:
            self.always_on_top = not self.always_on_top
            self.root.attributes('-topmost', self.always_on_top)
            self.draw()
        elif 10 <= event.x <= 62 and 10 <= event.y <= 64:
            self.toggle()

    def hotkeys(self):
        self.user.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
        self.user.PeekMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND,
                                         wintypes.UINT, wintypes.UINT, wintypes.UINT]
        current = None
        msg = wintypes.MSG()
        try:
            while True:
                try:
                    requested = self.hotkey_updates.get_nowait()
                except queue.Empty:
                    requested = None
                if requested is not None and requested != current:
                    modifiers, key = preferences.shortcut_parts(requested)
                    # Register a second ID first so a conflict preserves the old binding.
                    new_id = 2 if getattr(self, '_hotkey_id', 1) == 1 else 1
                    if self.user.RegisterHotKey(None, new_id, 0x4000 | modifiers, key):
                        if current is not None:
                            self.user.UnregisterHotKey(None, self._hotkey_id)
                        self._hotkey_id = new_id
                        current = requested
                        self.events.put(('shortcut_set', requested))
                    else:
                        self.events.put(('shortcut_error', requested + ' unavailable · choose another'))
                while self.user.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):
                    if msg.message == 0x0312 and msg.wParam == getattr(self, '_hotkey_id', 0):
                        self.events.put(('toggle', None))
                time.sleep(0.03)
        finally:
            if current is not None:
                self.user.UnregisterHotKey(None, self._hotkey_id)

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
        window.title('SimpleWhisper settings')
        window.configure(bg='#171b23')
        window.attributes('-topmost', True)
        window.resizable(False, False)
        style = ttk.Style(window)
        style.theme_use('clam')
        style.configure('Dark.TCombobox', fieldbackground='#252c39', background='#333d4c',
                        foreground='#f2f5fa', arrowcolor='#f2f5fa', bordercolor='#536176', padding=5)
        style.map('Dark.TCombobox',
                  fieldbackground=[('disabled', '#252c39'), ('readonly', '#252c39')],
                  foreground=[('disabled', '#a6b1c1'), ('readonly', '#f2f5fa')],
                  selectbackground=[('readonly', '#35465c')],
                  selectforeground=[('readonly', '#ffffff')],
                  background=[('active', '#42516a'), ('readonly', '#333d4c')])
        window.option_add('*TCombobox*Listbox.background', '#252c39')
        window.option_add('*TCombobox*Listbox.foreground', '#f2f5fa')
        window.option_add('*TCombobox*Listbox.selectBackground', '#42516a')
        window.option_add('*TCombobox*Listbox.selectForeground', '#ffffff')
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
        tk.Label(window, text='Activation shortcut', bg='#171b23', fg='#eef2f8').pack(
            anchor='w', padx=16, pady=(12, 4))
        shortcut = tk.StringVar(value=self.shortcut)
        binding = tk.Entry(window, textvariable=shortcut, state='readonly', readonlybackground='#252c39',
                           fg='#f2f5fa', insertbackground='white', relief='flat', font=('Segoe UI', 10))
        binding.pack(fill='x', padx=16, ipady=6)
        binding.bind('<Button-1>', lambda event: binding.focus_set())
        def capture(event):
            if self.listening:
                return 'break'
            key = event.keysym.upper()
            if key in {'CONTROL_L', 'CONTROL_R', 'ALT_L', 'ALT_R', 'SHIFT_L', 'SHIFT_R'}:
                return 'break'
            modifiers = [name for name, mask in [('Ctrl', 0x4), ('Alt', 0x20000), ('Shift', 0x1)]
                         if event.state & mask]
            value = '+'.join(modifiers + [key])
            if preferences.valid_shortcut(value):
                shortcut.set(value)
            return 'break'
        binding.bind('<KeyPress>', capture)
        tk.Label(window, text='Click the shortcut field, then press Ctrl or Alt + a key.',
                 bg='#171b23', fg='#c5cfdd').pack(anchor='w', padx=16, pady=(4, 0))
        tk.Label(window, text='Turn listening off before changing these settings.' if self.listening else
                 'Listening continues until you turn it off. No automatic timeout.',
                 bg='#171b23', fg='#a6b1c1').pack(padx=16, pady=12)
        def apply():
            self.microphone = mic.get()
            index = model.current()
            chosen = self.models[index]['id'] if 0 <= index < len(self.models) else self.model
            try:
                preferences.save(self.microphone, chosen, shortcut=self.shortcut)
            except OSError:
                self.note = 'Settings could not be saved.'
            window.destroy()
            self.settings_window = None
            if shortcut.get() != self.shortcut:
                self.hotkey_updates.put(shortcut.get())
            if chosen != self.model:
                self.busy = True
                self.note = 'Loading speech model…'
                self.draw()
                threading.Thread(target=self.load_models, args=(chosen,), daemon=True).start()
        tk.Button(window, text='Save', command=apply, state='disabled' if self.listening or self.busy else 'normal',
                  bg='#303b4b', fg='white', activebackground='#42516a', activeforeground='white',
                  relief='flat', padx=20, pady=5).pack(anchor='e', padx=16, pady=(0, 14))
        window.update_idletasks()
        self.desktop.dark_title(window)

    def toggle(self):
        if self.closing or self.shutdown_failed:
            return
        if self.listening:
            self.stop()
            self.enqueue_audio(None, None)
            self.note = 'Off · click the microphone to listen'
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
                    # Recording a shortcut in Settings must never start capture.
                    if not (self.settings_window and self.settings_window.winfo_exists()):
                        self.toggle()
                elif event == 'container_stopped':
                    self.close()
                    return
                elif event == 'models':
                    self.models = value['models']
                    self.model = value['active']
                    self.busy = False
                    self.note = 'Off · click the microphone to listen'
                elif event == 'shortcut_set':
                    self.shortcut = value
                    try:
                        preferences.save(self.microphone, preferences.load().get('model', self.model), shortcut=value)
                    except OSError:
                        self.note = 'Shortcut active · could not save setting'
                elif event == 'shortcut_error':
                    self.note = value
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
