import RPi.GPIO as GPIO
import board  # <--- ADD THIS LINE BACK
import adafruit_dht
import time
import datetime
import threading
import sqlite3
import json
from flask import Flask, request, jsonify, send_from_directory

# --- Flask & DB Setup ---
app = Flask(__name__)
DATABASE = 'hydroponics.db' # This file will be created in the same directory

def get_db():
    """Gets a new database connection."""
    conn = sqlite3.connect(DATABASE, check_same_thread=False) # Allow connection from multiple threads
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database and tables if they don't exist."""
    with app.app_context():
        db = get_db()
        cursor = db.cursor()

        # --- Settings Table ---
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        ''')

        # --- Sensor Readings Table ---
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS sensor_readings (
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            temperature REAL,
            humidity REAL,
            waterLevelOK INTEGER,  -- 1 for True, 0 for False
            floater1 INTEGER,  -- 1 for OK (HIGH), 0 for LOW
            floater2 INTEGER,
            floater3 INTEGER
        )
        ''')

        # --- Latest State Table ---
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS latest_state (
            key TEXT PRIMARY KEY,
            temperature REAL,
            humidity REAL,
            waterLevelOK INTEGER,
            floater1 INTEGER,
            floater2 INTEGER,
            floater3 INTEGER,
            last_updated DATETIME
        )
        ''')

        # Add columns if they don't exist (for migration)
        try:
            cursor.execute("ALTER TABLE sensor_readings ADD COLUMN floater1 INTEGER DEFAULT 0")
        except:
            pass
        try:
            cursor.execute("ALTER TABLE sensor_readings ADD COLUMN floater2 INTEGER DEFAULT 0")
        except:
            pass
        try:
            cursor.execute("ALTER TABLE sensor_readings ADD COLUMN floater3 INTEGER DEFAULT 0")
        except:
            pass
        try:
            cursor.execute("ALTER TABLE latest_state ADD COLUMN floater1 INTEGER DEFAULT 0")
        except:
            pass
        try:
            cursor.execute("ALTER TABLE latest_state ADD COLUMN floater2 INTEGER DEFAULT 0")
        except:
            pass
        try:
            cursor.execute("ALTER TABLE latest_state ADD COLUMN floater3 INTEGER DEFAULT 0")
        except:
            pass

        # --- Default Settings ---
        default_settings = {
            "lightsOnTime": "06:00", "lightsOffTime": "22:00",  # Shared for all lights in auto mode
            "pumpOnDuration": 900, "pumpOffDuration": 2700,  # Shared for all pumps in cycle mode
            "exhaustFanTempHigh": 27.0, "exhaustFanTempLow": 23.0, "exhaustFanHumidHigh": 65.0,
            "exhaustFanHumidLow": 55.0,  # Shared for all exhaust fans in auto mode
            "circulationFanOnDuration": 1800, "circulationFanOffDuration": 1800,  # Shared for all circulation fans in cycle mode
            "waterSystemMode": "auto",
            "maxFillTime": 600  # 10 minutes max fill time
        }
        # Individual modes
        for i in range(1, 7):  # Lights 1-6
            default_settings[f"lightsMode{i}"] = "schedule"
        for i in range(1, 6):  # Pumps 1-5
            default_settings[f"pumpMode{i}"] = "cycle"
        for i in range(1, 3):  # Exhaust fans 1-2
            default_settings[f"exhaustFanMode{i}"] = "auto"
        for i in range(1, 3):  # Circulation fans 1-2
            default_settings[f"circulationFanMode{i}"] = "cycle"

        for key, value in default_settings.items():
            cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))

        # Ensure 'latest_state' has a row
        cursor.execute("INSERT OR IGNORE INTO latest_state (key, temperature, humidity, waterLevelOK, floater1, floater2, floater3) VALUES ('sensors', 0, 0, 0, 0, 0, 0)")

        db.commit()
        db.close()
        print("Database initialized successfully.")

# --- GPIO Pin Definitions (BCM numbering) ---
# !!! UPDATE THESE PINS if they differ from your last script !!!
# Lights: 6 pins
LIGHTS_PINS = [6, 7, 8, 9, 20, 21]
# Pumps: 5 pins
PUMPS_PINS = [27, 5, 10, 11, 12]
# Exhaust Fans: 2 pins (env fans)
EXHAUST_FANS_PINS = [13, 16]
# Circulation Fans: 2 pins (air fans)
CIRCULATION_FANS_PINS = [19, 26]
# DHT Sensors: 2 pins
DHT_PINS_BCM = [4, 18]  # Corresponds to board.D4, board.D18
# Float Sensors: 3 pins
FLOAT_SENSORS_PINS = [17, 23, 24]
# Overflow Sensor: 1 pin
OVERFLOW_SENSOR_PIN = 25
SOLENOID_RELAY_PIN = 22

# DHT Sensor Setup
# Use multiple sensors
dht_devices = []
for pin in DHT_PINS_BCM:
    dht_devices.append(adafruit_dht.DHT11(getattr(board, f'D{pin}')))
    # dht_devices.append(adafruit_dht.DHT22(getattr(board, f'D{pin}')))

# --- GPIO Setup ---
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
relay_pins = LIGHTS_PINS + PUMPS_PINS + EXHAUST_FANS_PINS + CIRCULATION_FANS_PINS + [SOLENOID_RELAY_PIN]
for pin in relay_pins:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.HIGH) # Initialize all relays to OFF (LOW-triggered)
# Float sensors: pull-up, HIGH = water low (empty), LOW = water OK (full)
for pin in FLOAT_SENSORS_PINS:
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
# Overflow sensor: pull-up, HIGH = no overflow, LOW = overflow
GPIO.setup(OVERFLOW_SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
print("GPIO pins initialized.")

# --- Global State ---
hardware_state = {
    "pumps_on": [False] * len(PUMPS_PINS),
    "last_pumps_toggle": [time.monotonic()] * len(PUMPS_PINS),
    "lights_on": [False] * len(LIGHTS_PINS),
    "last_lights_toggle": [time.monotonic()] * len(LIGHTS_PINS),  # For lights, maybe not needed, but for consistency
    "exhaust_fans_on": [False] * len(EXHAUST_FANS_PINS),
    "last_exhaust_fans_toggle": [time.monotonic()] * len(EXHAUST_FANS_PINS),
    "circulation_fans_on": [False] * len(CIRCULATION_FANS_PINS),
    "last_circulation_fans_toggle": [time.monotonic()] * len(CIRCULATION_FANS_PINS),
    "solenoid_on": False,
    "solenoid_start_time": None,
    "water_error": None,  # "timeout", "reservoir_empty", "overflow"
    "last_sensor_log_time": time.monotonic() - 301 # Log sensors on first run
}
# Threading event to stop the loop
shutdown_event = threading.Event()

# --- Relay Control Function ---
def toggle_relay(pin, desired_state_on, component_name):
    """Controls a relay, printing only when state changes."""
    try:
        current_gpio_state = GPIO.input(pin)
        is_currently_on = (current_gpio_state == GPIO.LOW)

        if desired_state_on and not is_currently_on:
            GPIO.output(pin, GPIO.LOW) # Turn ON
            print(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {component_name} TURNED ON")
            return True
        elif not desired_state_on and is_currently_on:
            GPIO.output(pin, GPIO.HIGH) # Turn OFF
            print(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {component_name} TURNED OFF")
            return False
        return is_currently_on
    except Exception as e:
        print(f"Error toggling relay {component_name} (Pin {pin}): {e}")
        return False # Assume off on error

# --- Hardware Control Loop (Runs in a separate thread) ---
def run_hardware_loop():
    """This is the main hardware control loop, modified to use SQLite."""
    print("Hardware control loop starting...")
    
    while not shutdown_event.is_set():
        try:
            # --- 0. Load Settings from DB ---
            app_settings = {}
            db = get_db()
            cursor = db.cursor()
            rows = cursor.execute("SELECT key, value FROM settings").fetchall()
            db.close()
            
            for row in rows:
                # Convert types from string as needed
                key, value = row['key'], row['value']
                try:
                    # Try to convert to float or int
                    if '.' in value:
                        app_settings[key] = float(value)
                    else:
                        app_settings[key] = int(value)
                except ValueError:
                    # Keep as string if conversion fails (e.g., "auto", "06:00")
                    app_settings[key] = value
            
            # Get current times
            current_time_obj = datetime.datetime.now()
            current_time_for_schedule = current_time_obj.time()
            monotonic_time = time.monotonic()
            
            # --- 1. Lights Control ---
            on_time = datetime.datetime.strptime(str(app_settings.get("lightsOnTime", "06:00")), "%H:%M").time()
            off_time = datetime.datetime.strptime(str(app_settings.get("lightsOffTime", "22:00")), "%H:%M").time()

            if on_time <= off_time: # Normal day
                schedule_on = (on_time <= current_time_for_schedule < off_time)
            else: # Overnight
                schedule_on = (current_time_for_schedule >= on_time or current_time_for_schedule < off_time)

            for i, pin in enumerate(LIGHTS_PINS):
                mode = app_settings.get(f"lightsMode{i+1}", "schedule")
                if mode == "schedule":
                    should_on = schedule_on
                elif mode == "on":
                    should_on = True
                else: # "off"
                    should_on = False
                toggle_relay(pin, should_on, f"Light {i+1}")

            # --- 2. Hydroponic Pumps Control ---
            pump_on_duration = float(app_settings.get("pumpOnDuration", 900))
            pump_off_duration = float(app_settings.get("pumpOffDuration", 2700))

            for i, pin in enumerate(PUMPS_PINS):
                mode = app_settings.get(f"pumpMode{i+1}", "cycle")
                if mode == "cycle":
                    if hardware_state["pumps_on"][i]:
                        if monotonic_time - hardware_state["last_pumps_toggle"][i] >= pump_on_duration:
                            hardware_state["pumps_on"][i] = toggle_relay(pin, False, f"Pump {i+1}")
                            hardware_state["last_pumps_toggle"][i] = monotonic_time
                    else: # Pump is OFF
                        if monotonic_time - hardware_state["last_pumps_toggle"][i] >= pump_off_duration:
                            hardware_state["pumps_on"][i] = toggle_relay(pin, True, f"Pump {i+1}")
                            hardware_state["last_pumps_toggle"][i] = monotonic_time
                elif mode == "on":
                    toggle_relay(pin, True, f"Pump {i+1} (Manual ON)")
                else: # "off"
                    toggle_relay(pin, False, f"Pump {i+1} (Manual OFF)")

            # --- 3. Circulation Fans Control ---
            circ_on = float(app_settings.get("circulationFanOnDuration", 1800))
            circ_off = float(app_settings.get("circulationFanOffDuration", 1800))

            for i, pin in enumerate(CIRCULATION_FANS_PINS):
                mode = app_settings.get(f"circulationFanMode{i+1}", "cycle")
                if mode == "cycle":
                    if hardware_state["circulation_fans_on"][i]:
                        if monotonic_time - hardware_state["last_circulation_fans_toggle"][i] >= circ_on:
                            hardware_state["circulation_fans_on"][i] = toggle_relay(pin, False, f"Circulation Fan {i+1}")
                            hardware_state["last_circulation_fans_toggle"][i] = monotonic_time
                    else: # Fan is OFF
                        if monotonic_time - hardware_state["last_circulation_fans_toggle"][i] >= circ_off:
                            hardware_state["circulation_fans_on"][i] = toggle_relay(pin, True, f"Circulation Fan {i+1}")
                            hardware_state["last_circulation_fans_toggle"][i] = monotonic_time
                elif mode == "on":
                    toggle_relay(pin, True, f"Circulation Fan {i+1} (Manual ON)")
                else: # "off"
                    toggle_relay(pin, False, f"Circulation Fan {i+1} (Manual OFF)")

            # --- 4. Sensor Reading & Exhaust Fans Control ---
            temperatures = []
            humidities = []

            for i, dht in enumerate(dht_devices):
                try:
                    temp = dht.temperature
                    hum = dht.humidity
                    if temp is not None and hum is not None:
                        temperatures.append(temp)
                        humidities.append(hum)
                    else:
                        print(f"{current_time_obj.strftime('%H:%M:%S')} - DHT {i+1}: Failed to get reading.")
                except RuntimeError as error:
                    print(f"{current_time_obj.strftime('%H:%M:%S')} - DHT {i+1} Error: {error.args[0]}")
                except Exception as e:
                    print(f"{current_time_obj.strftime('%H:%M:%S')} - DHT {i+1} Unexpected Error: {e}")

            if temperatures and humidities:
                temperature_c = sum(temperatures) / len(temperatures)
                humidity = sum(humidities) / len(humidities)

                # --- 4a. Exhaust Fans ---
                temp_high = float(app_settings.get("exhaustFanTempHigh", 27.0))
                temp_low = float(app_settings.get("exhaustFanTempLow", 23.0))
                hum_high = float(app_settings.get("exhaustFanHumidHigh", 65.0))
                hum_low = float(app_settings.get("exhaustFanHumidLow", 55.0))

                should_auto_on = any(hardware_state["exhaust_fans_on"])  # Default to current
                if temperature_c > temp_high or humidity > hum_high:
                    should_auto_on = True
                elif temperature_c < temp_low and humidity < hum_low:
                    should_auto_on = False

                for i, pin in enumerate(EXHAUST_FANS_PINS):
                    mode = app_settings.get(f"exhaustFanMode{i+1}", "auto")
                    if mode == "auto":
                        toggle_relay(pin, should_auto_on, f"Exhaust Fan {i+1}")
                    elif mode == "on":
                        toggle_relay(pin, True, f"Exhaust Fan {i+1} (Manual ON)")
                    else: # "off"
                        toggle_relay(pin, False, f"Exhaust Fan {i+1} (Manual OFF)")

            else:
                temperature_c = None
                humidity = None
                print(f"{current_time_obj.strftime('%H:%M:%S')} - No valid DHT readings.")

            # --- 5. Water Level & Solenoid Control ---
            floater_states = [GPIO.input(pin) for pin in FLOAT_SENSORS_PINS]  # 0 LOW (OK), 1 HIGH (LOW water)
            water_levels_ok = [state == GPIO.LOW for state in floater_states]  # True if OK
            water_level_ok = all(water_levels_ok)  # All must be OK
            overflow_detected = GPIO.input(OVERFLOW_SENSOR_PIN) == GPIO.LOW  # LOW = overflow
            water_mode = app_settings.get("waterSystemMode", "auto")
            max_fill_time = float(app_settings.get("maxFillTime", 600))

            # Check for overflow - immediate shutdown
            if overflow_detected:
                hardware_state["water_error"] = "overflow"
                should_solenoid_be_on = False
                print(f"{current_time_obj.strftime('%H:%M:%S')} - OVERFLOW DETECTED! Shutting off solenoid.")
            else:
                # Check solenoid timeout
                if hardware_state["solenoid_on"] and hardware_state["solenoid_start_time"] is not None:
                    if monotonic_time - hardware_state["solenoid_start_time"] > max_fill_time:
                        if not water_level_ok:
                            hardware_state["water_error"] = "reservoir_empty"
                            print(f"{current_time_obj.strftime('%H:%M:%S')} - SOLENOID TIMEOUT: Reservoir may be empty!")
                        else:
                            hardware_state["water_error"] = "timeout"
                            print(f"{current_time_obj.strftime('%H:%M:%S')} - SOLENOID TIMEOUT: Stuck sensor?")
                        should_solenoid_be_on = False
                    else:
                        should_solenoid_be_on = True  # Keep on if within time
                else:
                    # Normal logic
                    should_solenoid_be_on = False
                    if water_mode == "auto":
                        if not water_level_ok and hardware_state["water_error"] != "reservoir_empty":
                            should_solenoid_be_on = True # Fill if water is low
                    elif water_mode == "fill":
                        should_solenoid_be_on = True
                        # Set mode back to "auto" in DB after starting the fill
                        try:
                            db = get_db()
                            db.execute("UPDATE settings SET value = 'auto' WHERE key = 'waterSystemMode'")
                            db.commit()
                            db.close()
                            print("Manual fill requested, resetting mode to 'auto' in DB.")
                        except Exception as e:
                            print(f"Error resetting manual fill mode: {e}")

            # Update solenoid state
            was_on = hardware_state["solenoid_on"]
            hardware_state["solenoid_on"] = toggle_relay(SOLENOID_RELAY_PIN, should_solenoid_be_on, "Water Solenoid")
            if hardware_state["solenoid_on"] and not was_on:
                hardware_state["solenoid_start_time"] = monotonic_time
                hardware_state["water_error"] = None  # Clear error on start
            elif not hardware_state["solenoid_on"] and was_on:
                hardware_state["solenoid_start_time"] = None

            # --- 6. Log Sensor Data to SQLite DB ---
            if monotonic_time - hardware_state["last_sensor_log_time"] >= 60: # Log every 1 min
                if temperature_c is not None and humidity is not None:
                    print("Logging sensor data to SQLite...")
                    try:
                        db = get_db()
                        db.execute(
                            "INSERT INTO sensor_readings (temperature, humidity, waterLevelOK, floater1, floater2, floater3) VALUES (?, ?, ?, ?, ?, ?)",
                            (temperature_c, humidity, 1 if water_level_ok else 0, 1 if water_levels_ok[0] else 0, 1 if water_levels_ok[1] else 0, 1 if water_levels_ok[2] else 0)
                        )
                        db.execute(
                            "UPDATE latest_state SET temperature = ?, humidity = ?, waterLevelOK = ?, floater1 = ?, floater2 = ?, floater3 = ?, last_updated = CURRENT_TIMESTAMP WHERE key = 'sensors'",
                            (temperature_c, humidity, 1 if water_level_ok else 0, 1 if water_levels_ok[0] else 0, 1 if water_levels_ok[1] else 0, 1 if water_levels_ok[2] else 0)
                        )
                        db.commit()
                        db.close()
                        hardware_state["last_sensor_log_time"] = monotonic_time
                        print("Log successful.")
                    except Exception as e:
                        print(f"Failed to log sensor data: {e}")
                else:
                    print("Skipping sensor log, DHT data is invalid.")

            # Main loop delay
            time.sleep(2) # Check logic every 2 seconds
            
        except Exception as e:
            print(f"CRITICAL ERROR in hardware loop: {e}")
            time.sleep(10) # Wait before retrying

# --- Flask API Endpoints ---

@app.route('/')
def index():
    """Serves the main dashboard.html file."""
    return send_from_directory('.', 'dashboard.html')

@app.route('/api/settings', methods=['GET'])
def get_settings():
    """Returns all current settings as JSON."""
    db = get_db()
    rows = db.execute("SELECT key, value FROM settings").fetchall()
    db.close()
    settings = {row['key']: row['value'] for row in rows}
    return jsonify(settings)

@app.route('/api/settings', methods=['POST'])
def update_settings():
    """Updates one or more settings in the DB."""
    data = request.json
    if not data:
        return jsonify({"error": "Invalid request"}), 400
    
    try:
        db = get_db()
        for key, value in data.items():
            db.execute("UPDATE settings SET value = ? WHERE key = ?", (str(value), key))
        db.commit()
        db.close()
        print(f"Updated settings: {data}")
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error updating settings: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/latest_sensors')
def get_latest_sensors():
    """Returns the most recent sensor readings."""
    db = get_db()
    row = db.execute("SELECT * FROM latest_state WHERE key = 'sensors'").fetchone()
    db.close()
    if row:
        data = dict(row)
        data["water_error"] = hardware_state.get("water_error")
        return jsonify(data)
    else:
        return jsonify({"error": "No sensor data found"}), 404

@app.route('/api/sensor_history')
def get_sensor_history():
    """Returns the last 20 sensor readings for the chart."""
    db = get_db()
    rows = db.execute("SELECT * FROM sensor_readings ORDER BY timestamp DESC LIMIT 20").fetchall()
    db.close()
    history = [dict(row) for row in rows]
    return jsonify(history)

# --- Main execution ---
if __name__ == '__main__':
    try:
        init_db() # Create DB and tables if they don't exist
        
        # Start the hardware control loop in a separate thread
        hardware_thread = threading.Thread(target=run_hardware_loop, daemon=True)
        hardware_thread.start()
        
        # Start the Flask web server
        print("\n--- Starting Web Server ---")
        print("Access your dashboard from any device on your network at:")
        print("http://<YOUR_PI_IP_ADDRESS>:5000\n")
        app.run(host='0.0.0.0', port=5000, debug=False)
        
    except KeyboardInterrupt:
        print("\nShutting down controller...")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        print("Stopping hardware loop and cleaning up GPIO...")
        shutdown_event.set() # Signal the hardware loop to exit
        if 'hardware_thread' in locals():
            hardware_thread.join(timeout=5) # Wait for thread to finish
        for dht in dht_devices:
            if dht:
                dht.exit() # Clean up DHT sensors
        GPIO.cleanup()
        print("Shutdown complete.")