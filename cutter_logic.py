import pigpio
import time

# --- STATE TRACKING ---
machine_state = "IDLE"
auto_target = 0
auto_current = 0
stop_requested = False

X_STEP = 17
X_DIR = 27
X_EN = 22          # Physical Pin 15
CC_STEP = 19       # Crosscut Step
CC_DIR = 26        # Crosscut Direction red wire
CC_EN = 23         # Physical Pin 16
CC_LIMIT = 14      # Crosscut Limit Switch

# --- HARDWARE CALIBRATION ---

# 1. FEED MOTOR (X-Axis)
FEED_WHEEL_DIAMETER_MM = 80.0
FEED_WHEEL_CIRCUMFERENCE = FEED_WHEEL_DIAMETER_MM * 3.14159
FEED_MICROSTEPS = 200 # 200 steps for 1 revolution (Full step)

# Calculate steps per millimeter dynamically: (200 / 251.3) = 0.795 steps per mm
STEPS_PER_MM = FEED_MICROSTEPS / FEED_WHEEL_CIRCUMFERENCE

# 2. CROSSCUT MOTOR (Linear Actuator)
# You need 9 revolutions to travel 120mm.
CC_REVOLUTIONS = 9
# 400 steps for 1 revolution (Full step)
CC_STEPS = 400 
MAX_CROSSCUT_STEPS = int(CC_REVOLUTIONS * CC_STEPS) 

# Initialize pigpio daemon connection
pi = pigpio.pi()
if not pi.connected:
    print("Error: pigpio daemon not running. Run 'sudo pigpiod' first.")
    exit()

# Setup Pins
pi.set_mode(X_STEP, pigpio.OUTPUT)
pi.set_mode(X_DIR, pigpio.OUTPUT)
pi.set_mode(X_EN, pigpio.OUTPUT)
pi.set_mode(CC_STEP, pigpio.OUTPUT)
pi.set_mode(CC_DIR, pigpio.OUTPUT)
pi.set_mode(CC_EN, pigpio.OUTPUT)
pi.set_mode(CC_LIMIT, pigpio.INPUT)
pi.set_pull_up_down(CC_LIMIT, pigpio.PUD_UP) # Internal pull-up for the switch

# Disable motors by default so they run cool (1 = disabled, 0 = enabled)
pi.write(X_EN, 1)
pi.write(CC_EN, 1)

def enable_x():
    pi.write(X_EN, 0)
    print("X-Axis enabled.")
    time.sleep(0.05)

def disable_x():
    print("X-Axis disabled.")
    pi.write(X_EN, 1)

def enable_cc():
    print("Crosscut enabled.")
    pi.write(CC_EN, 0)
    time.sleep(0.05)

def disable_cc():
    print("Crosscut disabled.")
    pi.write(CC_EN, 1)

def _execute_wave(step_pin, dir_pin, direction, total_steps, start_delay_us, min_delay_us):
    global stop_requested
    if stop_requested: return

    pi.write(dir_pin, direction)
    pulses = []
    wave_ids = []
    
    ramp_steps = int(total_steps * 0.05) # 5% ramp up, 20% ramp down
    
    for i in range(total_steps):
        if i < ramp_steps:
            delay = start_delay_us - int((start_delay_us - min_delay_us) * (i / ramp_steps))
        elif i > (total_steps - ramp_steps):
            steps_left = total_steps - i
            delay = start_delay_us - int((start_delay_us - min_delay_us) * (steps_left / ramp_steps))
        else:
            delay = min_delay_us
            
        pulses.append(pigpio.pulse(1<<step_pin, 0, int(delay/2)))
        pulses.append(pigpio.pulse(0, 1<<step_pin, int(delay/2)))
        
        # When we hit 2000 pulses, create a chunk so we don't crash!
        if len(pulses) >= 2000:
            pi.wave_add_generic(pulses)
            wid = pi.wave_create()
            if wid >= 0:
                wave_ids.append(wid)
            pulses = [] # Reset for next chunk
            
    # Add any leftover pulses
    if len(pulses) > 0:
        pi.wave_add_generic(pulses)
        wid = pi.wave_create()
        if wid >= 0:
            wave_ids.append(wid)
            
    if len(wave_ids) > 0:
        # Chain all the chunks together seamlessly!
        pi.wave_chain(wave_ids)
        
        # Wait for hardware to finish, but poll the stop button
        while pi.wave_tx_busy(): 
            if stop_requested:
                pi.wave_tx_stop() # Instantly kill the hardware wave
                break
            time.sleep(0.05)
            
        # Clean up memory
        for wid in wave_ids:
            pi.wave_delete(wid)

def home_crosscut():
    global stop_requested
    print("Homing crosscut...")
    pi.write(CC_DIR, 1) # Set to homing direction
    
    # Step slowly until switch goes HIGH (pressed / connection broken)
    while pi.read(CC_LIMIT) == 0:
        if stop_requested: break
        pi.write(CC_STEP, 1)
        time.sleep(0.002)
        pi.write(CC_STEP, 0)
        time.sleep(0.002)
    if not stop_requested:
        print("Crosscut homed.")

def move_x_direction(pad_size_mm, speed_factor, accel_factor, steps_per_mm):
    global stop_requested
    if stop_requested: return
    
    speed_factor = max(1, min(10, speed_factor))
    accel_factor = max(1, min(10, accel_factor))
    
    target_steps = int(pad_size_mm * steps_per_mm)
    
    # Map 1-10 UI input to EXTREMELY SLOW limits for testing
    min_delay = 6000 - int((speed_factor - 1) * 333)
    start_delay = 12000 - int((accel_factor - 1) * 666)
    
    print(f"Feeding {pad_size_mm}mm ({target_steps} steps)...")
    _execute_wave(X_STEP, X_DIR, 1, target_steps, start_delay, min_delay)

def perform_crosscut():
    global stop_requested
    if stop_requested: return

    print('Ensuring crosscut is home before starting...')
    home_crosscut()
    if stop_requested: return
    
    min_delay = 675
    start_delay = 10200
    
    print("Cutting forward...")
    _execute_wave(CC_STEP, CC_DIR, 0, MAX_CROSSCUT_STEPS, start_delay, min_delay)
    if stop_requested: return
    
    print("Returning home...")
    _execute_wave(CC_STEP, CC_DIR, 1, MAX_CROSSCUT_STEPS, start_delay, min_delay)
    if stop_requested: return
    
    home_crosscut()

# --- STATE WRAPPERS (Called by Flask) ---

def run_home():
    global machine_state
    machine_state = "HOMING"
    enable_cc()
    home_crosscut()
    disable_cc()
    machine_state = "IDLE"

def run_test_x(pad_size_mm, feed_speed, feed_accel, steps_per_mm):
    global machine_state
    machine_state = "TESTING_X"
    enable_x()
    move_x_direction(pad_size_mm, feed_speed, feed_accel, steps_per_mm)
    disable_x()
    machine_state = "IDLE"

def run_test_crosscut():
    global machine_state
    machine_state = "TESTING_CROSSCUT"
    enable_cc()
    perform_crosscut()
    disable_cc()
    machine_state = "IDLE"

def auto_mode(pad_size_mm, feed_speed, feed_accel, target_quantity, steps_per_mm):
    global machine_state, auto_target, auto_current, stop_requested
    
    machine_state = "AUTO_MODE"
    auto_target = int(target_quantity)
    auto_current = 0
    stop_requested = False
    
    enable_cc()
    enable_x()
    
    home_crosscut() 
    
    # Loop exactly the number of times requested
    for current_pad in range(auto_target):
        if stop_requested:
            print("Auto mode STOPPED by user.")
            break
            
        auto_current = current_pad + 1
        move_x_direction(pad_size_mm, feed_speed, feed_accel, steps_per_mm)
        perform_crosscut()
        print(f"Progress: Cut {auto_current} of {auto_target}")
        
    disable_cc()
    disable_x()
    machine_state = "IDLE"
    stop_requested = False

