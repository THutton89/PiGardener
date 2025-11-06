# hydroponics_controller.py
import RPi.GPIO as GPIO
import board
import adafruit_dht
import time
import datetime

# --- User Adjustable Configuration ---
# GPIO Pin Definitions (BCM numbering)
LIGHTS_PIN = 6
PUMP_PIN = 27
ENV_FAN_PIN = 13
AIR_FAN_PIN = 19
DHT_PIN_BCM = 4  # Corresponds to board.D4

# Lights Schedule (24-hour format)
LIGHTS_ON_TIME = datetime.time(6, 0)   # 6:00 AM
LIGHTS_OFF_TIME = datetime.time(22, 0) # 10:00 PM

# Hydroponic Pump Cycle (seconds)
PUMP_ON_DURATION = 15 * 60  # 15 minutes
PUMP_OFF_DURATION = 45 * 60 # 45 minutes

# Environmental Fan Control Thresholds
TEMP_HIGH_THRESHOLD = 27.0  # Celsius, turn fan ON above this
TEMP_LOW_THRESHOLD = 23.0   # Celsius, turn fan OFF below this
HUMIDITY_HIGH_THRESHOLD = 65.0 # Percent, turn fan ON above this
HUMIDITY_LOW_THRESHOLD = 55.0  # Percent, turn fan OFF below this

# Air Circulation Fan Cycle (seconds)
AIR_FAN_ON_DURATION = 30
AIR_FAN_OFF_DURATION = 30
# --- End of User Adjustable Configuration ---

# DHT Sensor Setup (Change to DHT22 if you have that model)
dht_device = adafruit_dht.DHT11(board.D4)
# dht_device = adafruit_dht.DHT22(board.D4)

# GPIO Setup
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Outputs for Relays
relay_pins = [LIGHTS_PIN, PUMP_PIN, ENV_FAN_PIN, AIR_FAN_PIN]
for pin in relay_pins:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.HIGH) # Initialize all relays to OFF (assuming LOW-triggered)

print("Hydroponics Controller Initializing...")
print(f"  Lights: Pin {LIGHTS_PIN}, ON {LIGHTS_ON_TIME} - OFF {LIGHTS_OFF_TIME}")
print(f"  Pump: Pin {PUMP_PIN}, ON {PUMP_ON_DURATION//60}min, OFF {PUMP_OFF_DURATION//60}min")
print(f"  Env Fan: Pin {ENV_FAN_PIN}, Temp >{TEMP_HIGH_THRESHOLD}C / <{TEMP_LOW_THRESHOLD}C, Hum >{HUMIDITY_HIGH_THRESHOLD}% / <{HUMIDITY_LOW_THRESHOLD}%")
print(f"  Air Fan: Pin {AIR_FAN_PIN}, Cycle {AIR_FAN_ON_DURATION}s ON / {AIR_FAN_OFF_DURATION}s OFF")
print("Controller Running. Press CTRL+C to exit.")
print("-" * 30)

# State variables for timed operations using time.monotonic()
last_pump_toggle_time = time.monotonic()
pump_is_on = False
GPIO.output(PUMP_PIN, GPIO.HIGH) # Start with pump OFF

last_air_fan_toggle_time = time.monotonic()
air_fan_is_on = False
GPIO.output(AIR_FAN_PIN, GPIO.HIGH) # Start with air fan OFF

env_fan_is_on = False # Tracks state of environmental fan

def toggle_relay(pin, desired_state_on, component_name):
    """
    Controls a relay, printing only when state changes.
    desired_state_on: True if component should be ON, False if OFF.
    Relays are assumed LOW-triggered (LOW = ON, HIGH = OFF).
    Returns the new actual state (True if ON, False if OFF).
    """
    current_gpio_state = GPIO.input(pin) # Read current physical state
    is_currently_on = (current_gpio_state == GPIO.LOW)

    if desired_state_on and not is_currently_on:
        GPIO.output(pin, GPIO.LOW) # Turn ON
        print(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {component_name} TURNED ON")
        return True
    elif not desired_state_on and is_currently_on:
        GPIO.output(pin, GPIO.HIGH) # Turn OFF
        print(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {component_name} TURNED OFF")
        return False
    return is_currently_on # No change, return current on-state


try:
    while True:
        current_time_obj = datetime.datetime.now()
        current_time_for_schedule = current_time_obj.time()
        monotonic_time = time.monotonic()

        # 1. Lights Control
        if LIGHTS_ON_TIME <= LIGHTS_OFF_TIME: # Normal day schedule (e.g. ON 06:00, OFF 22:00)
            should_lights_be_on = (LIGHTS_ON_TIME <= current_time_for_schedule < LIGHTS_OFF_TIME)
        else: # Overnight schedule (e.g. ON 20:00, OFF 08:00 next day)
            should_lights_be_on = (current_time_for_schedule >= LIGHTS_ON_TIME or current_time_for_schedule < LIGHTS_OFF_TIME)
        toggle_relay(LIGHTS_PIN, should_lights_be_on, "Lights")

        # 2. Hydroponic Pump Control
        if pump_is_on:
            if monotonic_time - last_pump_toggle_time >= PUMP_ON_DURATION:
                pump_is_on = toggle_relay(PUMP_PIN, False, "Hydro Pump")
                last_pump_toggle_time = monotonic_time
        else: # Pump is OFF
            if monotonic_time - last_pump_toggle_time >= PUMP_OFF_DURATION:
                pump_is_on = toggle_relay(PUMP_PIN, True, "Hydro Pump")
                last_pump_toggle_time = monotonic_time
        
        # 3. Environmental Fan Control (Temp/Humidity)
        try:
            temperature_c = dht_device.temperature
            humidity = dht_device.humidity

            if temperature_c is not None and humidity is not None:
                # Uncomment to see readings every cycle
                # print(f"DEBUG: Temp={temperature_c:.1f}C, Hum={humidity:.1f}%")

                # --- REFINED HYSTERESIS LOGIC ---
                if temperature_c > TEMP_HIGH_THRESHOLD or humidity > HUMIDITY_HIGH_THRESHOLD:
                    # Condition to TURN ON
                    should_env_fan_be_on = True
                elif temperature_c < TEMP_LOW_THRESHOLD and humidity < HUMIDITY_LOW_THRESHOLD:
                    # Condition to TURN OFF (only if both are low)
                    should_env_fan_be_on = False
                else:
                    # In the "dead-band" (between low and high thresholds)
                    # Hold the current state
                    should_env_fan_be_on = env_fan_is_on
                
                # Apply the desired state and update the state variable
                env_fan_is_on = toggle_relay(ENV_FAN_PIN, should_env_fan_be_on, "Env Fan")
                # --- END OF REFINED LOGIC ---

            else:
                print(f"{current_time_obj.strftime('%Y-%m-%d %H:%M:%S')} - DHT: Failed to get reading for Env Fan.")
        except RuntimeError as error:
            print(f"{current_time_obj.strftime('%Y-%m-%d %H:%M:%S')} - DHT Error: {error.args[0]}")
        except Exception as e:
            print(f"{current_time_obj.strftime('%Y-%m-%d %H:%M:%S')} - DHT Unexpected Error: {e}")

        # 4. Air Circulation Fan Control
        if air_fan_is_on:
            if monotonic_time - last_air_fan_toggle_time >= AIR_FAN_ON_DURATION:
                air_fan_is_on = toggle_relay(AIR_FAN_PIN, False, "Air Circ Fan")
                last_air_fan_toggle_time = monotonic_time
        else: # Air fan is OFF
            if monotonic_time - last_air_fan_toggle_time >= AIR_FAN_OFF_DURATION:
                air_fan_is_on = toggle_relay(AIR_FAN_PIN, True, "Air Circ Fan")
                last_air_fan_toggle_time = monotonic_time

        # Main loop delay - controls how often sensors are read and logic is checked
        time.sleep(5) # Check conditions every 5 seconds

except KeyboardInterrupt:
    print("\nExiting controller due to user interrupt.")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
finally:
    print("Cleaning up GPIO pins and exiting.")
    if 'dht_device' in locals() and dht_device:
        dht_device.exit()
    GPIO.cleanup()