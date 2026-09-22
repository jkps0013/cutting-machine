import pigpio
import time

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
    """
    Internal helper function to generate and execute a smooth pigpio hardware waveform.
    Builds the acceleration and deceleration pulse chain.
    """
    pi.write(dir_pin, direction)
    pulses = []
    ramp_steps = int(total_steps * 0.2) # 20% ramp up, 20% ramp down
    
    for i in range(total_steps):
        if i < ramp_steps:
            # Ramping up (decreasing delay)
            delay = start_delay_us - int((start_delay_us - min_delay_us) * (i / ramp_steps))
        elif i > (total_steps - ramp_steps):
            # Ramping down (increasing delay)
            steps_left = total_steps - i
            delay = start_delay_us - int((start_delay_us - min_delay_us) * (steps_left / ramp_steps))
        else:
            # Cruising at max speed
            delay = min_delay_us
            
        # Add pulse: (GPIO on, GPIO off, delay in microseconds)
        pulses.append(pigpio.pulse(1<<step_pin, 0, int(delay/2)))
        pulses.append(pigpio.pulse(0, 1<<step_pin, int(delay/2)))
        
    pi.wave_clear()
    pi.wave_add_generic(pulses)
    wave_id = pi.wave_create()
    
    if wave_id >= 0:
        pi.wave_send_once(wave_id)
        while pi.wave_tx_busy(): # Wait for hardware to finish sending the wave
            time.sleep(0.1)
        pi.wave_delete(wave_id)

def home_crosscut():
    """
    Slowly drives the crosscut knife in the negative direction until the limit switch is pressed.
    """
    print("Homing crosscut...")
    pi.write(CC_DIR, 0) # Set to homing direction
    
    # Step slowly until switch goes LOW (pressed)
    while pi.read(CC_LIMIT) == 1:
        pi.write(CC_STEP, 1)
        time.sleep(0.002)
        pi.write(CC_STEP, 0)
        time.sleep(0.002)
    print("Crosscut homed.")

def move_x_direction(pad_size_mm, speed_factor, accel_factor):
    """
    Moves the foil forward based on the selected pad size (12.7, 30, or 42mm).
    Translates UI speed/accel factors into microsecond delays.
    """
    target_steps = int(pad_size_mm * STEPS_PER_MM)
    min_delay = max(500, int(3000 / speed_factor))     # Faster speed = lower delay
    start_delay = max(2000, int(10000 / accel_factor)) # Faster accel = lower starting delay
    
    print(f"Feeding {pad_size_mm}mm ({target_steps} steps)...")
    _execute_wave(X_STEP, X_DIR, 1, target_steps, start_delay, min_delay)

def perform_crosscut(speed_factor, accel_factor):
    """
    Drives crosscut to the max rail limit, then returns it to home position.
    """
    min_delay = max(500, int(3000 / speed_factor))
    start_delay = max(2000, int(10000 / accel_factor))
    
    print("Cutting forward...")
    _execute_wave(CC_STEP, CC_DIR, 1, MAX_CROSSCUT_STEPS, start_delay, min_delay)
    
    print("Returning home...")
    _execute_wave(CC_STEP, CC_DIR, 0, MAX_CROSSCUT_STEPS, start_delay, min_delay)
    # Ensure it's perfectly zeroed against the switch
    home_crosscut()

def auto_mode(pad_size_mm, feed_speed, feed_accel, cut_speed, cut_accel, target_quantity):
    """
    Continuous loop: Feed X, then Crosscut, repeating for the specified quantity.
    """
    home_crosscut() # Must be home before starting
    
    # Loop exactly the number of times requested
    for current_pad in range(int(target_quantity)):
        move_x_direction(pad_size_mm, feed_speed, feed_accel)
        perform_crosscut(cut_speed, cut_accel)
        print(f"Progress: Cut {current_pad + 1} of {target_quantity}")
        
    print(f"Auto mode complete. {target_quantity} pads processed.")