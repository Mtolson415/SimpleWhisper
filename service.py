"""Bounded WAV gateway and allowlisted Docker Whisper model selection."""
import io
import json
import threading
import urllib.error
import urllib.request
import uuid
import wave
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

UPSTREAM = 'http://whisper:8080/inference'
MODEL = 'Whisper-Base'
CATALOG = {
    'base': ('Base — English + Spanish (fast)', 'ggml-base.bin'),
    'base-en': ('Base.en — English only (fast)', 'ggml-base.en.bin'),
    'turbo': ('Large-v3 Turbo — multilingual (slower CPU)', 'ggml-large-v3-turbo.bin'),
}
ACTIVE_MODEL = 'base'
LIMIT = 4 * 1024 * 1024
BUSY = threading.Lock()


def model_catalog():
    return {'active': ACTIVE_MODEL, 'models': [{'id': key, 'label': value[0]} for key, value in CATALOG.items()]}


def select_model(model):
    global ACTIVE_MODEL
    if model not in CATALOG:
        raise ValueError('Unknown model')
    boundary = uuid.uuid4().hex
    body = (f'--{boundary}\r\nContent-Disposition: form-data; name="model"\r\n\r\n'
            f'/models/{CATALOG[model][1]}\r\n--{boundary}--\r\n').encode()
    request = urllib.request.Request('http://whisper:8080/load', body,
                                    {'Content-Type': 'multipart/form-data; boundary=' + boundary})
    with urllib.request.urlopen(request, timeout=180) as response:
        response.read()
    ACTIVE_MODEL = model
    return model_catalog()


def validate_audio(data):
    with wave.open(io.BytesIO(data), 'rb') as audio:
        if (audio.getnchannels(), audio.getsampwidth(), audio.getframerate()) != (1, 2, 16000):
            raise ValueError('Expected mono 16-bit 16000 Hz WAV')
        frames = audio.getnframes()
        if not 1600 <= frames <= 16000 * 120:
            raise ValueError('Recording must be 0.1 to 120 seconds')
        if len(audio.readframes(frames)) != frames * 2:
            raise ValueError('Incomplete WAV recording')


def transcribe(data):
    validate_audio(data)
    boundary = uuid.uuid4().hex
    body = (f'--{boundary}\r\nContent-Disposition: form-data; name="model"\r\n\r\n{MODEL}\r\n'
            f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="dictation.wav"\r\n'
            'Content-Type: audio/wav\r\n\r\n').encode() + data + f'\r\n--{boundary}--\r\n'.encode()
    request = urllib.request.Request(UPSTREAM, body, {'Content-Type': 'multipart/form-data; boundary=' + boundary})
    with urllib.request.urlopen(request, timeout=180) as response:
        result = json.load(response)
    if not isinstance(result.get('text'), str):
        raise ValueError('Whisper returned no transcript')
    return result['text'].strip()


class Handler(BaseHTTPRequestHandler):
    def reply(self, status, result):
        body = json.dumps(result).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == '/models':
            return self.reply(200, model_catalog())
        self.reply(200 if self.path == '/health' else 404,
                   {'status': 'ok', 'scope': 'gateway only'} if self.path == '/health' else {'error': 'Not found'})

    def do_POST(self):
        self.connection.settimeout(15)
        if self.path == '/models/select':
            if self.headers.get('Origin') or self.headers.get('Content-Type') != 'application/json':
                return self.reply(403, {'error': 'Native JSON clients only'})
            if not BUSY.acquire(blocking=False):
                return self.reply(429, {'error': 'Transcription or model change already running'})
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 1024:
                    raise ValueError('Invalid selection request')
                request = json.loads(self.rfile.read(size))
                self.reply(200, select_model(request.get('model')))
            except (ValueError, TypeError, AttributeError):
                self.reply(400, {'error': 'Choose a listed model'})
            except Exception:
                self.reply(502, {'error': 'Model could not load; check mounted model files'})
            finally:
                BUSY.release()
            return
        if self.path != '/transcribe':
            return self.reply(404, {'error': 'Not found'})
        # Browser pages must not be able to submit recordings to this local API.
        if self.headers.get('Origin') or self.headers.get('Content-Type') != 'audio/wav':
            return self.reply(403, {'error': 'Native WAV clients only'})
        if not BUSY.acquire(blocking=False):
            return self.reply(429, {'error': 'Transcription already running'})
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= LIMIT:
                raise ValueError('Recording too large or empty')
            data = self.rfile.read(size)
            if len(data) != size:
                raise ValueError('Incomplete request')
            self.reply(200, {'text': transcribe(data)})
        except (ValueError, wave.Error, EOFError):
            self.reply(400, {'error': 'Invalid WAV or transcription response'})
        except Exception:
            self.reply(502, {'error': 'Whisper container unavailable; check Docker'})
        finally:
            BUSY.release()

    def log_message(self, *args):
        pass  # Never log recordings or transcripts.


if __name__ == '__main__':
    ThreadingHTTPServer(('0.0.0.0', 8080), Handler).serve_forever()
