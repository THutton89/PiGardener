# lights_fans_test.py
import RPi.GPIO as GPIO
import board
import adafruit_dht
import time

# --- Pin Definitions (BCM numbering) ---
# !!! UPDATE THESE PINS TO MATCH YOUR WIRING !!!
LIGHTS_RELAY_PIN = 6
ENV_FAN_RELAY_PIN = 12  # Fan for temperature/humidity control
AIR_FAN_RELAY_PIN = 12  # Fan for 30s on/off air circulation

# DHT Sensor (using board.D4, which is BCM GPIO 4)
DHT_SENSOR_PIN_BCM = 4
dht_device = adafruit_dht.DHT11(board.D4) # Or adafruit_dht.DHT22(board.D4)

# --- Test Parameters ---
LIGHTS_ON_DURATION_TEST = 10  # seconds
ENV_FAN_ON_DURATION_TEST = 15 # seconds
AIR_FAN_ON_DURATION = 30      # seconds
AIR_FAN_OFF_DURATION = 30     # seconds
AIR_FAN_CYCLES_TEST = 2       # Number of on/off cycles for air fan

# Environmental Fan Triggers (for test)
TEMP_THRESHOLD_HIGH = 26.0  # Celsius
HUMIDITY_THRESHOLD_HIGH = 70.0 # Percent

# --- GPIO Setup ---
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Outputs for Relays
GPIO.setup(LIGHTS_RELAY_PIN, GPIO.OUT)
GPIO.setup(ENV_FAN_RELAY_PIN, GPIO.OUT)
GPIO.setup(AIR_FAN_RELAY_PIN, GPIO.OUT)

# Initialize relays to OFF state (assuming LOW-triggered relays, so HIGH is OFF)
# If your relays are HIGH-triggered, swap GPIO.HIGH and GPIO.LOW here and in tests.
GPIO.output(LIGHTS_RELAY_PIN, GPIO.HIGH)
GPIO.output(ENV_FAN_RELAY_PIN, GPIO.HIGH)
GPIO.output(AIR_FAN_RELAY_PIN, GPIO.HIGH)
print("Initial: All relays (Lights, Env Fan, Air Fan) set to OFF.")

print("--- Lights and Fans Test Script ---")
print(f"Lights Relay Pin: {LIGHTS_RELAY_PIN}")
print(f"Environmental Fan Relay Pin: {ENV_FAN_RELAY_PIN}")
print(f"Air Circulation Fan Relay Pin: {AIR_FAN_RELAY_PIN}")
print(f"DHT Sensor Pin: BCM {DHT_SENSOR_PIN_BCM}")
print("-" * 40)

try:
    # 1. Test Lights
    print("Testing Lights...")
    print(f"Turning Lights ON for {LIGHTS_ON_DURATION_TEST} seconds.")
    GPIO.output(LIGHTS_RELAY_PIN, GPIO.LOW) # Turn ON
    time.sleep(LIGHTS_ON_DURATION_TEST)
    GPIO.output(LIGHTS_RELAY_PIN, GPIO.HIGH) # Turn OFF
    print("Lights OFF.")
    print("-" * 40)
    time.sleep(1)

    # 2. Test Environmental Fan (based on DHT sensor)
    print("Testing Environmental Fan (Temperature & Humidity based)...")
    try:
        temperature_c = dht_device.temperature
        humidity = dht_device.humidity

        if temperature_c is not None and humidity is not None:
            print(f"Current Temperature: {temperature_c:.1f}°C")
            print(f"Current Humidity:    {humidity:.1f}%")

            fan_activated = False
            if temperature_c > TEMP_THRESHOLD_HIGH:
                print(f"Temperature ({temperature_c:.1f}°C) is above threshold ({TEMP_THRESHOLD_HIGH}°C).")
                fan_activated = True
            if humidity > HUMIDITY_THRESHOLD_HIGH:
                print(f"Humidity ({humidity:.1f}%) is above threshold ({HUMIDITY_THRESHOLD_HIGH}%).")
                fan_activated = True
            
            if fan_activated:
                print(f"Turning Environmental Fan ON for {ENV_FAN_ON_DURATION_TEST} seconds.")
                GPIO.output(ENV_FAN_RELAY_PIN, GPIO.LOW) # Turn ON
                time.sleep(ENV_FAN_ON_DURATION_TEST)
                GPIO.output(ENV_FAN_RELAY_PIN, GPIO.HIGH) # Turn OFF
                print("Environmental Fan OFF.")
            else:
                print("Conditions are within defined thresholds. Environmental Fan not activated.")
        else:
            print("Failed to read from DHT sensor for Environmental Fan test.")
            
    except RuntimeError as error:
        print(f"DHT Runtime Error for Env Fan test: {error.args[0]}")
    except Exception as e:
        print(f"Unexpected error with DHT for Env Fan test: {e}")
    print("-" * 40)
    time.sleep(1)

    # 3. Test Air Circulation Fan (Timer based)
    print("Testing Air Circulation Fan (30s ON / 30s OFF)...")
    for i in range(AIR_FAN_CYCLES_TEST):
        print(f"Cycle {i+1}/{AIR_FAN_CYCLES_TEST}:")
        print(f"Turning Air Circulation Fan ON for {AIR_FAN_ON_DURATION} seconds.")
        GPIO.output(AIR_FAN_RELAY_PIN, GPIO.LOW) # Turn ON
        time.sleep(AIR_FAN_ON_DURATION)
        
        print(f"Turning Air Circulation Fan OFF for {AIR_FAN_OFF_DURATION} seconds.")
        GPIO.output(AIR_FAN_RELAY_PIN, GPIO.HIGH) # Turn OFF
        time.sleep(AIR_FAN_OFF_DURATION)
    print("Air Circulation Fan test complete.")
    print("-" * 40)
    
    print("All tests complete.")

except KeyboardInterrupt:
    print("\nTest aborted by user.")
except Exception as e:
    print(f"An error occurred: {e}")
finally:
    print("Cleaning up GPIO pins.")
    if 'dht_device' in locals() and dht_device:
        dht_device.exit()
    GPIO.cleanup()
