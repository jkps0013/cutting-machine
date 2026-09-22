import pigpio
import time

# --- STATE TRACKING ---
machine_state = "IDLE"
auto_target = 0
auto_current = 0
stop_requested = False

# Pin Definitions
X_STEP = 17
X_DIR = 27
CC_STEP = 22       # Crosscut Step
CC_DIR = 23        # Crosscut Direction
CC_LIMIT = 24      # Crosscut Limit Switch

# Constants based on hardware definitions
STEPS_PER_MM = 6.366
MAX_CROSSCUT_STEPS = 5000  # Update this after measuring your physical rail

# Initialize pigpio daemon connection
pi = pigpio.pi()
if not pi.connected:
    print("Error: pigpio daemon not running. Run 'sudo pigpiod' first.")
    exit()

# Setup Pins
pi.set_mode(X_STEP, pigpio.OUTPUT)
pi.set_mode(X_DIR, pigpio.OUTPUT)
pi.set_mode(CC_STEP, pigpio.OUTPUT)
pi.set_mode(CC_DIR, pigpio.OUTPUT)
pi.set_mode(CC_LIMIT, pigpio.INPUT)
pi.set_pull_up_down(CC_LIMIT, pigpio.PUD_UP) # Internal pull-up for the switch

def _execute_wave(step_pin, dir_pin, direction, total_steps, start_delay_us, min_delay_us):
    global stop_requested
    if stop_requested: return

    pi.write(dir_pin, direction)
    pulses = []
    ramp_steps = int(total_steps * 0.2) # 20% ramp up, 20% ramp down
    
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
        
    pi.wave_clear()
    pi.wave_add_generic(pulses)
    wave_id = pi.wave_create()
    
    if wave_id >= 0:
        pi.wave_send_once(wave_id)
        # Wait for hardware to finish, but poll the stop button
        while pi.wave_tx_busy(): 
            if stop_requested:
                pi.wave_tx_stop() # Instantly kill the hardware wave
                break
            time.sleep(0.05)
        pi.wave_delete(wave_id)

def home_crosscut():
    global stop_requested
    print("Homing crosscut...")
    pi.write(CC_DIR, 0) # Set to homing direction
    
    # Step slowly until switch goes LOW (pressed)
    while pi.read(CC_LIMIT) == 1:
        if stop_requested: break
        pi.write(CC_STEP, 1)
        time.sleep(0.002)
        pi.write(CC_STEP, 0)
        time.sleep(0.002)
    if not stop_requested:
        print("Crosscut homed.")

def move_x_direction(pad_size_mm, speed_factor, accel_factor):
    global stop_requested
    if stop_requested: return
    target_steps = int(pad_size_mm * STEPS_PER_MM)
    min_delay = max(500, int(3000 / speed_factor))     
    start_delay = max(2000, int(10000 / accel_factor)) 
    
    print(f"Feeding {pad_size_mm}mm ({target_steps} steps)...")
    _execute_wave(X_STEP, X_DIR, 1, target_steps, start_delay, min_delay)

def perform_crosscut(speed_factor, accel_factor):
    global stop_requested
    if stop_requested: return
    min_delay = max(500, int(3000 / speed_factor))
    start_delay = max(2000, int(10000 / accel_factor))
    
    print("Cutting forward...")
    _execute_wave(CC_STEP, CC_DIR, 1, MAX_CROSSCUT_STEPS, start_delay, min_delay)
    if stop_requested: return
    
    print("Returning home...")
    _execute_wave(CC_STEP, CC_DIR, 0, MAX_CROSSCUT_STEPS, start_delay, min_delay)
    if stop_requested: return
    
    home_crosscut()

# --- STATE WRAPPERS (Called by Flask) ---

def run_home():
    global machine_state
    machine_state = "HOMING"
    home_crosscut()
    machine_state = "IDLE"

def run_test_x(pad_size_mm, feed_speed, feed_accel):
    global machine_state
    machine_state = "TESTING_X"
    move_x_direction(pad_size_mm, feed_speed, feed_accel)
    machine_state = "IDLE"

def run_test_crosscut(cut_speed, cut_accel):
    global machine_state
    machine_state = "TESTING_CROSSCUT"
    perform_crosscut(cut_speed, cut_accel)
    machine_state = "IDLE"

def auto_mode(pad_size_mm, feed_speed, feed_accel, cut_speed, cut_accel, target_quantity):
    global machine_state, auto_target, auto_current, stop_requested
    
    machine_state = "AUTO_MODE"
    auto_target = int(target_quantity)
    auto_current = 0
    stop_requested = False
    
    home_crosscut() 
    
    # Loop exactly the number of times requested
    for current_pad in range(auto_target):
        if stop_requested:
            print("Auto mode STOPPED by user.")
            break
            
        auto_current = current_pad + 1
        move_x_direction(pad_size_mm, feed_speed, feed_accel)
        perform_crosscut(cut_speed, cut_accel)
        print(f"Progress: Cut {auto_current} of {auto_target}")
        
    machine_state = "IDLE"
    stop_requested = False