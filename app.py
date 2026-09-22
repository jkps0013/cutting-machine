from flask import Flask, request, jsonify, render_template
import threading
import cutter_logic

app = Flask(__name__)

# Run long hardware tasks in background threads
def run_in_background(func, *args):
    thread = threading.Thread(target=func, args=args)
    thread.start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/home', methods=['POST'])
def home():
    run_in_background(cutter_logic.home_crosscut)
    return jsonify({"status": "Homing initiated"})

@app.route('/api/test_x', methods=['POST'])
def test_x():
    data = request.json
    run_in_background(cutter_logic.move_x_direction, float(data['size']), float(data['feed_speed']), float(data['feed_accel']))
    return jsonify({"status": "X-Direction test started"})

@app.route('/api/test_crosscut', methods=['POST'])
def test_crosscut():
    data = request.json
    run_in_background(cutter_logic.perform_crosscut, float(data['cut_speed']), float(data['cut_accel']))
    return jsonify({"status": "Crosscut test started"})

@app.route('/api/auto', methods=['POST'])
def auto():
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
    return jsonify({"status": f"Auto mode started for {data['quantity']} pads"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)