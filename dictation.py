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
from transcript_quality import clean_transcript
from rolling_audio import RollingPhraseBuffer, LatestJobs
from revision_span import RevisionSpan
from windows_clipboard import set_clipboard_text
from windows_input import paste_shortcut

ENDPOINT = 'http://127.0.0.1:17863/transcribe'
RATE = 16000
AUTO_STOP = {'Never': None, 'After 2 minutes': 120, 'After 5 minutes': 300,
             'After 15 minutes': 900, 'After 30 minutes': 1800}


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


def watch_containers():
    guard = singleton('LocalWhisperDictationWatcher')
    if not guard:
        return
    previously_running = False
    failures = 0
    while True:
        running = gateway_running()
        if running is None:
            failures += 1
            if failures >= 3:
                previously_running = False
            time.sleep(2)
            continue
        failures = 0
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
        self.root.title('Local Whisper Dictation 0.3.1')
        self.root.geometry('640x460')
        self.root.minsize(600, 420)
        self.events = queue.Queue()
        self.stream = None
        self.busy = True  # Wait for the startup model selection before capture.
        self.chunks = []
        self.frames = 0
        self.target = None
        self.record_live = False
        self.record_continuous = False
        self.record_rolling = False
        self.session_limit_seconds = None
        self.live_paste_suppressed = False
        self.pending_pastes = []
        self.status = tk.StringVar(value='Click a text field in another app. Ctrl+Alt+D starts/stops.')
        panel = ttk.Frame(self.root, padding=12)
        panel.pack(fill='both', expand=True)
        panel.columnconfigure(1, weight=1)
        panel.rowconfigure(5, weight=1)
        ttk.Label(panel, textvariable=self.status, wraplength=560).grid(
            row=0, column=0, columnspan=2, sticky='ew', pady=(0, 10))
        self.devices = [None]
        names = ['Windows default microphone']
        for index, device in enumerate(sd.query_devices()):
            if device['max_input_channels'] > 0:
                self.devices.append(index)
                names.append(f"{index}: {device['name']}")
        ttk.Label(panel, text='Microphone').grid(row=1, column=0, sticky='w', padx=(0, 10))
        self.microphone = ttk.Combobox(panel, values=names, state='readonly', width=35)
        self.microphone.current(0)
        self.microphone.grid(row=1, column=1, sticky='ew', pady=3)
        self.model_ids = []
        ttk.Label(panel, text='Speech model').grid(row=2, column=0, sticky='w', padx=(0, 10))
        self.model_selector = ttk.Combobox(panel, values=['Loading speech models…'], state='disabled', width=35)
        self.model_selector.current(0)
        self.model_selector.grid(row=2, column=1, sticky='ew', pady=3)
        self.model_selector.bind('<<ComboboxSelected>>', self.change_model)
        self.direct_input = tk.BooleanVar(value=True)
        options = ttk.Frame(panel)
        options.grid(row=3, column=0, columnspan=2, sticky='ew', pady=(8, 4))
        options.columnconfigure(0, weight=1)
        options.columnconfigure(1, weight=1)
        ttk.Checkbutton(options, text='Dictate into active text box',
                        variable=self.direct_input).grid(row=0, column=0, sticky='w', pady=3)
        self.live_input = tk.BooleanVar(value=True)
        self.live_checkbox = ttk.Checkbutton(options, text='Live phrases at pauses',
                                             variable=self.live_input)
        self.live_checkbox.grid(row=1, column=0, sticky='w', pady=3)
        self.continuous_input = tk.BooleanVar(value=True)
        self.continuous_checkbox = ttk.Checkbutton(options, text='Continuous listening',
            variable=self.continuous_input, command=lambda: self.live_input.set(True) if self.continuous_input.get() else None)
        self.continuous_checkbox.grid(row=1, column=1, sticky='w', pady=3)
        timeout = ttk.Frame(options)
        timeout.grid(row=2, column=1, sticky='w', pady=3)
        ttk.Label(timeout, text='Auto-stop').pack(side='left', padx=(0, 6))
        self.auto_stop = ttk.Combobox(timeout, values=list(AUTO_STOP), state='readonly', width=18)
        self.auto_stop.current(0)
        self.auto_stop.pack(side='left')
        self.rolling_input = tk.BooleanVar(value=False)
        self.rolling_checkbox = ttk.Checkbutton(options,
            text='Rolling drafts (experimental)', variable=self.rolling_input,
            command=lambda: self.live_input.set(True) if self.rolling_input.get() else None)
        self.rolling_checkbox.grid(row=2, column=0, sticky='w', pady=3)
        self.always_on_top = tk.BooleanVar(value=False)
        ttk.Checkbutton(options, text='Always on top', variable=self.always_on_top,
                        command=self.set_always_on_top).grid(row=0, column=1, sticky='w', pady=3)
        ttk.Label(panel, text='Transcript preview').grid(row=4, column=0, columnspan=2, sticky='w', pady=(4, 4))
        transcript = ttk.Frame(panel)
        transcript.grid(row=5, column=0, columnspan=2, sticky='nsew')
        self.preview = tk.Text(transcript, height=6, width=40, wrap='word', padx=8, pady=6)
        scrollbar = ttk.Scrollbar(transcript, command=self.preview.yview)
        self.preview.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        self.preview.pack(side='left', fill='both', expand=True)
        ttk.Button(panel, text='Copy transcript', command=self.copy).grid(
            row=6, column=0, columnspan=2, sticky='e', pady=(8, 0))
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

    def set_always_on_top(self):
        self.root.attributes('-topmost', self.always_on_top.get())

    def monitor_container(self):
        failures = 0
        while True:
            state = gateway_running()
            failures = failures + 1 if state is None else 0
            if state is False or failures >= 3:
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
            self.events.put(('audio_warning', 'Microphone warning; some audio may be missing. Still listening.'))
        limit = self.session_limit_seconds if self.record_continuous else 120
        if limit is not None and self.frames + frames > RATE * limit:
            self.events.put(('limit', None))
            return
        if self.record_live:
            if self.record_rolling:
                job = self.segmenter.feed(bytes(data))
                if job:
                    self.phrases.put(job)
                self.frames += frames
                return
            phrase = self.segmenter.add(bytes(data))
            if phrase:
                try:
                    self.phrases.put_nowait(phrase)
                except queue.Full:
                    try:
                        self.phrases.get_nowait()
                    except queue.Empty:
                        pass
                    try:
                        self.phrases.put_nowait(phrase)
                    except queue.Full:
                        pass
                    self.events.put(('audio_warning', 'Transcription fell behind; skipped a queued phrase. Still listening.'))
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
        self.pending_pastes.clear()
        self.chunks = []
        self.frames = 0
        self.record_live = self.live_input.get()
        if self.continuous_input.get():
            self.record_live = True
            self.live_input.set(True)
        self.record_continuous = self.record_live and self.continuous_input.get()
        self.session_limit_seconds = AUTO_STOP[self.auto_stop.get()]
        self.record_rolling = self.record_live and self.rolling_input.get()
        if self.record_live:
            self.segmenter = RollingPhraseBuffer() if self.record_rolling else PhraseBuffer()
            self.phrases = LatestJobs() if self.record_rolling else queue.Queue(maxsize=8)
            self.draft_phrase = None
            self.completed_text = ''
            self.draft_span = None
            self.draft_inserted = False
            self.live_paste_suppressed = False
            self.preview.delete('1.0', 'end')
            worker = self.recognize_drafts if self.record_rolling else self.recognize_phrases
            threading.Thread(target=worker, daemon=True).start()
        try:
            self.stream = sd.RawInputStream(device=self.devices[self.microphone.current()],
                                            samplerate=RATE, channels=1, dtype='int16', callback=self.audio)
            self.stream.start()
            self.status.set('Rolling drafts — updates while speaking; Ctrl+Alt+D stops.' if self.record_rolling else
                            'Live phrases — pause briefly for text; Ctrl+Alt+D stops.' if self.record_live
                            else 'Recording — Ctrl+Alt+D to stop. Maximum two minutes.')
        except Exception as error:
            self.stop()
            if self.record_live:
                self.busy = True
                self.finish_phrases()
            self.status.set('Microphone failed: ' + str(error))

    def finish_phrases(self):
        if self.record_rolling:
            job = self.segmenter.finish()
            if job:
                self.phrases.put(job)
            self.phrases.put(None)
            return
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

    def recognize_drafts(self):
        jobs = self.phrases
        while True:
            job = jobs.get()
            if job is None:
                break
            try:
                text = self.transcribe_pcm(job['audio'])
                self.events.put(('draft_text', (job['phrase'], text, job['final'])))
            except Exception:
                self.events.put(('live_error', 'A rolling update failed; still listening.'))
        self.events.put(('live_finished', None))

    def remember_draft(self, span, text, final):
        if not span.record(text):
            self.live_paste_suppressed = True
            self.status.set('Could not verify the inserted span. Revisions stopped; use the preview.')
        if final and self.draft_span is span:
            self.draft_span = None

    def render_draft(self, phrase, text, final):
        text = clean_transcript(text)
        if self.draft_phrase != phrase:
            self.draft_phrase = phrase
            self.draft_span = None
            self.draft_inserted = False
            self.draft_prefix = ' ' if self.completed_text else ''
            self.draft_last = ''
        shown = self.completed_text + self.draft_prefix + text
        self.preview.delete('1.0', 'end')
        self.preview.insert('1.0', shown[-20000:])
        if text and self.direct_input.get() and not self.live_paste_suppressed:
            if self.user.GetForegroundWindow() != self.target:
                self.live_paste_suppressed = True
            elif not any(self.user.GetAsyncKeyState(key) & 0x8000 for key in (0x10, 0x11, 0x12, ord('D'))):
                outgoing = self.draft_prefix + text
                if not self.draft_inserted:
                    span = RevisionSpan.begin()
                    if final or span is not None:
                        if self.insert(outgoing, live=True):
                            self.draft_inserted = True
                            self.draft_last = outgoing
                            self.draft_span = span
                            if span:
                                self.root.after(100, lambda s=span, t=outgoing, f=final: self.remember_draft(s, t, f))
                    else:
                        self.status.set('Rolling preview active. This field gets final phrases; safe revisions unavailable.')
                elif outgoing != self.draft_last:
                    span = self.draft_span
                    if span and span.prepare_revision():
                        if self.insert(outgoing, live=True):
                            self.draft_last = outgoing
                            self.root.after(100, lambda s=span, t=outgoing, f=final: self.remember_draft(s, t, f))
                    else:
                        self.live_paste_suppressed = True
                        self.status.set('Caret or draft changed. Automatic revisions stopped; use the preview.')
        if final:
            self.completed_text = shown[-20000:]

    def transcribe_pcm(self, pcm):
        request = urllib.request.Request(ENDPOINT, wav_bytes(pcm), {'Content-Type': 'audio/wav'})
        with urllib.request.urlopen(request, timeout=190) as response:
            return clean_transcript(json.load(response)['text'])

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
        set_clipboard_text(self.root.winfo_id(), text)

    def flush_pastes(self):
        if not self.pending_pastes:
            return
        if (not self.direct_input.get() or self.live_paste_suppressed
                or self.user.GetForegroundWindow() != self.target):
            self.pending_pastes.clear()
            self.live_paste_suppressed = True
            self.status.set('Destination changed. Transcript retained; use Copy transcript.')
            return
        if any(self.user.GetAsyncKeyState(key) & 0x8000 for key in (0x10, 0x11, 0x12, ord('D'))):
            return
        text = ''.join(self.pending_pastes)
        self.pending_pastes.clear()
        self.insert(text, live=True)

    def insert(self, text, attempts=0, live=False):
        prefix = text[:len(text) - len(text.lstrip(' \t'))]
        cleaned = clean_transcript(text)
        text = prefix + cleaned if cleaned else ''
        if not text:
            if not live:
                self.busy = False
            return
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
                if sum(map(len, self.pending_pastes)) + len(text) > 20000:
                    self.pending_pastes.clear()
                    self.live_paste_suppressed = True
                    self.status.set('Pending paste limit reached. Transcript retained; use Copy transcript.')
                    return False
                self.pending_pastes.append(text)
                self.status.set('Release shortcut keys to paste the pending phrase.')
                return
            if attempts < 40:
                self.root.after(50, lambda: self.insert(text, attempts + 1))
            else:
                self.busy = False
                self.status.set('Release shortcut keys. Transcript retained; use Copy transcript.')
            return
        try:
            self.copy(text)
        except OSError:
            if not live:
                self.busy = False
            self.status.set('Clipboard busy. Transcript retained in preview; try Copy transcript.')
            return False
        # Never send Enter or submit a form. Clipboard retains the transcript.
        try:
            paste_shortcut()
        except OSError:
            if not live:
                self.busy = False
            self.status.set('Windows blocked paste. Use Copy transcript; elevated apps are unsupported.')
            return False
        if not live:
            self.busy = False
        self.status.set('Live phrase pasted; Ctrl+Alt+D stops recording.' if live and self.stream else
                        'Paste requested. Review text in your app. Ctrl+Alt+D for another recording.')
        return True

    def poll(self):
        self.flush_pastes()
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
                elif event == 'draft_text':
                    self.render_draft(*value)
                elif event == 'live_text' and value:
                    prefix = ' ' if self.preview.get('1.0', 'end-1c') else ''
                    self.preview.insert('end', prefix + value)
                    if len(self.preview.get('1.0', 'end-1c')) > 20000:
                        self.preview.delete('1.0', 'end-20001c')
                    self.insert(prefix + value, live=True)
                elif event == 'live_finished':
                    self.busy = False
                    self.status.set('Live recording finished. Review the transcript.')
                elif event == 'live_error':
                    self.status.set(value)
                elif event == 'audio_warning':
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
        self.continuous_checkbox.configure(state='disabled' if self.busy or self.stream else 'normal')
        self.auto_stop.configure(state='disabled' if self.busy or self.stream else 'readonly')
        self.rolling_checkbox.configure(state='disabled' if self.busy or self.stream else 'normal')
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
