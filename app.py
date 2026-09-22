from flask import Flask, request, jsonify, render_template
import threading
import cutter_logic

import logging

app = Flask(__name__)

# Mute the default Flask HTTP request spam
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# Run long hardware tasks in background threads
def run_in_background(func, *args):
    thread = threading.Thread(target=func, args=args)
    thread.start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/status', methods=['GET'])
def get_status():
    return jsonify({
        "state": cutter_logic.machine_state,
        "current": cutter_logic.auto_current,
        "target": cutter_logic.auto_target
    })

@app.route('/api/stop', methods=['POST'])
def stop_machine():
    cutter_logic.stop_requested = True
    return jsonify({"status": "Stopping..."})

@app.route('/api/home', methods=['POST'])
def home():
    if cutter_logic.machine_state != "IDLE": return jsonify({"status": "Busy"})
    run_in_background(cutter_logic.run_home)
    return jsonify({"status": "Homing initiated"})

@app.route('/api/test_x', methods=['POST'])
def test_x():
    if cutter_logic.machine_state != "IDLE": return jsonify({"status": "Busy"})
    data = request.json
    run_in_background(cutter_logic.run_test_x, float(data['size']), float(data['feed_speed']), float(data['feed_accel']))
    return jsonify({"status": "X-Direction test started"})

@app.route('/api/test_crosscut', methods=['POST'])
def test_crosscut():
    if cutter_logic.machine_state != "IDLE": return jsonify({"status": "Busy"})
    data = request.json
    run_in_background(cutter_logic.run_test_crosscut, float(data['cut_speed']), float(data['cut_accel']))
    return jsonify({"status": "Crosscut test started"})

@app.route('/api/auto', methods=['POST'])
def auto():
    if cutter_logic.machine_state != "IDLE": return jsonify({"status": "Busy"})
    data = request.json
    run_in_background(
        cutter_logic.auto_mode, 
        float(data['size']), 
        float(data['feed_speed']), 
        float(data['feed_accel']),
        float(data['cut_speed']), 
        float(data['cut_accel']),
        int(data['quantity'])
    )
    return jsonify({"status": "Auto mode started"})

import socket

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

if __name__ == '__main__':
    local_ip = get_local_ip()
    print("\n==================================================")
    print(" Pad Machine Control Server Started!")
    print(" Access on this computer: http://localhost:5000")
    print(f" Access on your network:  http://{local_ip}:5000")
    print("==================================================\n")
    app.run(host='0.0.0.0', port=5000, debug=False)