import RPi.GPIO as GPIO
import board
import adafruit_dht
import time

# --- Pin Definitions (BCM numbering) ---
SOIL_SENSOR_DO_PIN = 20  # Soil Moisture Sensor Digital Output
RELAY_PIN_PUMP_1 = 5     # Relay IN pin for Pump 1
RELAY_PIN_PUMP_2 = 26    # Relay IN pin for Pump 2 (NEW)
# DHT_PIN is handled by board.D4

# Initialize DHT device for CircuitPython
# For DHT11:
dht_device = adafruit_dht.DHT11(board.D4) # board.D4 corresponds to BCM pin 4
# If you had a DHT22, it would be:
# dht_device = adafruit_dht.DHT22(board.D4)

# --- GPIO Setup ---
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

GPIO.setup(SOIL_SENSOR_DO_PIN, GPIO.IN)
GPIO.setup(RELAY_PIN_PUMP_1, GPIO.OUT)
GPIO.setup(RELAY_PIN_PUMP_2, GPIO.OUT) # NEW: Setup for Pump 2

# Initialize relays to OFF state (assuming LOW-triggered relays, so HIGH is OFF)
GPIO.output(RELAY_PIN_PUMP_1, GPIO.HIGH)
print("Initial: Pump 1 set to OFF.")
GPIO.output(RELAY_PIN_PUMP_2, GPIO.HIGH) # NEW: Initialize Pump 2 to OFF
print("Initial: Pump 2 set to OFF.")


print("--- Comprehensive Component Test (using CircuitPython for DHT) ---")
print(f"Soil Sensor DO Pin: {SOIL_SENSOR_DO_PIN}")
print(f"Relay (Pump 1) Pin: {RELAY_PIN_PUMP_1}")
print(f"Relay (Pump 2) Pin: {RELAY_PIN_PUMP_2}") # NEW
print(f"DHT Sensor Pin: BCM 4 (using board.D4)")
print(f"DHT Sensor Type: DHT11 (CircuitPython)")
print("-" * 30)

try:
    # 1. Test Soil Moisture Sensor
    print("Testing Soil Moisture Sensor...")
    time.sleep(1)
    moisture_level = GPIO.input(SOIL_SENSOR_DO_PIN)
    if moisture_level == GPIO.LOW:
        print("Soil Status: WET (DO Pin is LOW)")
    else:
        print("Soil Status: DRY (DO Pin is HIGH)")
    print("-" * 30)
    time.sleep(1)

    # 2. Test DHT Temperature and Humidity Sensor (using CircuitPython)
    print("Testing Temperature & Humidity Sensor (DHT with CircuitPython)...")
    try:
        # Attempt to get a sensor reading.
        temperature_c = dht_device.temperature
        humidity = dht_device.humidity
        # Note: CircuitPython DHT library can sometimes return None if reading fails
        if temperature_c is not None and humidity is not None:
            print(f"Temperature: {temperature_c:.1f}°C")
            print(f"Humidity:    {humidity:.1f}%")
        else:
            print("DHT sensor returned no data. Check wiring or try again.")
            
    except RuntimeError as error:
        # Errors happen fairly often, DHT's are tricky sensors!
        print(f"DHT (CircuitPython) Runtime Error: {error.args[0]}")
        print("Try again! If it persists, check wiring.")
    except Exception as e:
        print(f"Unexpected error with CircuitPython DHT: {e}")
    print("-" * 30)
    time.sleep(1)

    # 3. Test Pump Relay 1
    print("Testing Pump 1 Relay...")
    print(f"Turning PUMP 1 (GPIO {RELAY_PIN_PUMP_1}) ON for 5 seconds.")
    GPIO.output(RELAY_PIN_PUMP_1, GPIO.LOW) # Assuming LOW-triggered relay
    time.sleep(5)
    GPIO.output(RELAY_PIN_PUMP_1, GPIO.HIGH)
    print(f"Pump 1 (GPIO {RELAY_PIN_PUMP_1}) OFF.")
    print("-" * 30)
    time.sleep(1)

    # 4. Test Pump Relay 2 (NEW SECTION)
    print("Testing Pump 2 Relay...")
    print(f"Turning PUMP 2 (GPIO {RELAY_PIN_PUMP_2}) ON for 5 seconds.")
    GPIO.output(RELAY_PIN_PUMP_2, GPIO.LOW) # Assuming LOW-triggered relay
    time.sleep(5)
    GPIO.output(RELAY_PIN_PUMP_2, GPIO.HIGH)
    print(f"Pump 2 (GPIO {RELAY_PIN_PUMP_2}) OFF.")
    
    print("-" * 30)
    print("All tests complete.")

except KeyboardInterrupt:
    print("\nTest aborted by user.")

except Exception as e:
    print(f"An error occurred: {e}")

finally:
    print("Cleaning up GPIO pins.")
    if 'dht_device' in locals() and dht_device: # Check if dht_device was initialized
        dht_device.exit() # Release resources used by the CircuitPython DHT library
    GPIO.cleanup()
