import os
import queue
import threading
from flask import Flask, render_template, jsonify, request
from app_modules.log_monitor import LogMonitor
from app_modules.database import get_db, close_db, init_db, setup_database
from app_modules.logger_config import setup_logger


# Initialize logger and app
logger = setup_logger('app')
app = Flask(__name__)


# Setup database and global variables
setup_database(app)
monitor_thread = None
output_queue = queue.Queue()
should_stop = False

def get_should_stop():
    global should_stop
    return should_stop


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        data = request.json
        db = get_db()
        db.execute('DELETE FROM sftp_settings')
        db.execute('''
            INSERT INTO sftp_settings (hostname, port, username, password, remote_dir)
            VALUES (?, ?, ?, ?, ?)
        ''', (data['hostname'], int(data['port']), data['username'],
              data['password'], data['remote_dir']))
        db.commit()
        return jsonify({'status': 'success'})

    # For GET requests, fetch existing settings
    db = get_db()
    settings = db.execute('SELECT * FROM sftp_settings').fetchone()
    if request.headers.get('Content-Type') == 'application/json':
        return jsonify({
            'hostname': settings['hostname'] if settings else '',
            'port': settings['port'] if settings else '',
            'username': settings['username'] if settings else '',
            'password': settings['password'] if settings else '',
            'remote_dir': settings['remote_dir'] if settings else ''
        })

    return render_template('settings.html')



@app.route('/available-logs')
def get_available_logs():
    try:
        files = LogMonitor.get_available_logs()
        return jsonify({'files': files})
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@app.route('/start', methods=['POST'])
def start_monitoring():
    global monitor_thread, should_stop

    try:
        if monitor_thread is None or not monitor_thread.is_alive():
            log_file = request.json.get('logFile')
            if not log_file:
                return jsonify({'status': 'error', 'message': 'Log file is required'}), 400

            output_queue.put(f"Starting monitoring for log file: {log_file}")
            monitor = LogMonitor(log_file, output_queue)
            should_stop = False
            monitor_thread = threading.Thread(target=monitor.monitor, args=(get_should_stop,))
            monitor_thread.daemon = True
            monitor_thread.start()

            return jsonify({'status': 'started'})
        return jsonify({'status': 'already_running'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/stop', methods=['POST'])
def stop_monitoring():
    global monitor_thread, should_stop

    try:
        if monitor_thread and monitor_thread.is_alive():
            output_queue.put("Stopping monitoring...")
            should_stop = True
            monitor_thread.join(timeout=5)
            return jsonify({'status': 'stopped'})
        return jsonify({'status': 'not_running'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/output')
def get_output():
    try:
        lines = []
        while not output_queue.empty():
            lines.append(output_queue.get_nowait())
        return jsonify({'output': lines})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/pause', methods=['POST'])
def toggle_pause():
    try:
        data = request.json
        if monitor_thread and hasattr(monitor_thread, '_target'):
            monitor_thread._target.is_paused = data.get('isPaused', False)
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("LOG_MONITOR_PORT")), debug=True)