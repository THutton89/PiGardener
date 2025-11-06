import RPi.GPIO as GPIO
import time

# --- Pin Definitions (BCM numbering) ---
# !!! UPDATE THESE PINS !!!
FLOAT_SENSOR_PIN = 17  # GPIO pin connected to the float sensor
SOLENOID_RELAY_PIN = 22 # GPIO pin connected to the solenoid valve relay

# --- GPIO Setup ---
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Setup float sensor as an input.
# We use a pull-up resistor so the pin reads HIGH by default.
# When the float switch closes (water is present), it pulls the pin LOW.
#
# WIRING:
# - One float sensor wire to GPIO 17 (FLOAT_SENSOR_PIN)
# - The other float sensor wire to GND (Ground)
#
GPIO.setup(FLOAT_SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Setup solenoid relay as an output
GPIO.setup(SOLENOID_RELAY_PIN, GPIO.OUT)
# Initialize relay to OFF (assuming LOW-triggered, so HIGH is OFF)
GPIO.output(SOLENOID_RELAY_PIN, GPIO.HIGH)
print("Initial: Solenoid Valve set to OFF.")

print("--- Water System Test ---")
print(f"Float Sensor Pin: {FLOAT_SENSOR_PIN}")
print(f"Solenoid Relay Pin: {SOLENOID_RELAY_PIN}")
print("-" * 30)

try:
    # 1. Test Solenoid Valve
    print("Testing Solenoid Valve...")
    print(f"Turning Solenoid (GPIO {SOLENOID_RELAY_PIN}) ON for 10 seconds.")
    GPIO.output(SOLENOID_RELAY_PIN, GPIO.LOW) # Turn ON
    time.sleep(10)
    GPIO.output(SOLENOID_RELAY_PIN, GPIO.HIGH) # Turn OFF
    print(f"Solenoid (GPIO {SOLENOID_RELAY_PIN}) OFF.")
    print("-" * 30)
    time.sleep(1)

    # 2. Test Float Sensor
    print("Testing Float Sensor. Press CTRL+C to stop.")
    print("Please move the float sensor up and down.")
    
    current_state = -1 # Force initial print
    
    while True:
        pin_state = GPIO.input(FLOAT_SENSOR_PIN)
        
        if pin_state != current_state:
            if pin_state == GPIO.LOW:
                # Pin is LOW, so the switch is closed.
                print(f"{time.strftime('%H:%M:%S')} - Water Level: OK (Float is up, pin is LOW)")
            else:
                # Pin is HIGH, so the switch is open.
                print(f"{time.strftime('%H:%M:%S')} - Water Level: LOW (Float is down, pin is HIGH)")
            current_state = pin_state
            
        time.sleep(0.5) # Check every 0.5 seconds

except KeyboardInterrupt:
    print("\nTest aborted by user.")

except Exception as e:
    print(f"An error occurred: {e}")

finally:
    print("Cleaning up GPIO pins.")
    GPIO.cleanup()