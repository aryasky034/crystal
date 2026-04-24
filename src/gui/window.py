# ============================================================
#  CRYSTAL AI - Web UI Server  (Flask + SocketIO)
# ============================================================

import threading
import webbrowser
import time
import json as _json
import psutil
from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, emit
from src.utils.logger import get_logger

log = get_logger(__name__)

app    = Flask(__name__, template_folder='../../templates')
app.config['SECRET_KEY'] = 'crystal_secret'
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='threading')

# Shared brain reference (set by Window.__init__)
_brain = None


class Window:
    def __init__(self, brain, speaker, listener):
        global _brain
        self.brain    = brain
        self.speaker  = speaker
        self.listener = listener
        _brain = brain
        self._register_routes()
        log.info('Web UI ready')

    # ── ROUTES ────────────────────────────────
    def _register_routes(self):

        @app.route('/')
        def index():
            return render_template('index.html')

        @app.route('/api/news')
        def api_news():
            try:
                prompt = (
                    'Give me 8 current global news headlines. '
                    'Respond ONLY with a JSON array. Each item must have exactly: '
                    '"title" (string), "category" (one word: Tech/Politics/Science/Business/Health/World), '
                    '"time" (like "2h ago"). '
                    'Return ONLY valid JSON, no markdown, no explanation.'
                )
                raw = _brain.think(prompt).strip()
                if raw.startswith('```'):
                    raw = raw.split('\n', 1)[-1].rsplit('```', 1)[0]
                return jsonify(_json.loads(raw))
            except Exception as e:
                log.error(f'News API: {e}')
                return jsonify([
                    {'title': 'Ask Crystal for news analysis in the chat!',
                     'category': 'Info', 'time': 'now'}
                ])

        # ── SOCKET EVENTS ─────────────────────
        @socketio.on('user_message')
        def on_message(data):
            text = data.get('text', '').strip()
            if not text: return
            emit('status', {'state': 'thinking'})
            try:
                response = self.brain.think(text)
                emit('status',            {'state': 'speaking'})
                emit('crystal_response',  {'text': response})
                threading.Thread(target=self.speaker.speak,
                                 args=(response,), daemon=True).start()
            except Exception as e:
                log.error(f'Brain: {e}')
                emit('crystal_response', {'text': f'[Error: {e}]'})
            finally:
                emit('status', {'state': 'idle'})

        @socketio.on('start_listening')
        def on_listen():
            emit('status', {'state': 'listening'})
            try:
                text = self.listener.listen()
                emit('listening_result', {'text': text})
            except Exception as e:
                log.error(f'Listen: {e}')
                emit('listening_result', {'text': ''})

        @socketio.on('stop_listening')
        def on_stop():
            emit('status', {'state': 'idle'})

    # ── SYSTEM MONITOR ────────────────────────
    def _monitor(self):
        while True:
            try:
                cpu  = psutil.cpu_percent(interval=1)
                ram  = psutil.virtual_memory().percent
                try:
                    t    = psutil.sensors_temperatures()
                    temp = list(t.values())[0][0].current if t else None
                except Exception:
                    temp = None
                socketio.emit('system_stats', {'cpu': cpu, 'ram': ram, 'temp': temp})
            except Exception:
                pass
            time.sleep(2)

    # ── RUN ───────────────────────────────────
    def run(self):
        threading.Thread(target=self._monitor, daemon=True).start()

        def _open():
            time.sleep(1.5)
            webbrowser.open('http://localhost:5000')

        threading.Thread(target=_open, daemon=True).start()
        log.info('Server at http://localhost:5000')
        socketio.run(app, host='0.0.0.0', port=5000,
                     debug=False, use_reloader=False)