# Pi Gardener 🌱

A comprehensive Raspberry Pi-based hydroponics automation system with web dashboard, real-time monitoring, and safety features.

![Dashboard Preview](https://via.placeholder.com/800x400/10b981/ffffff?text=Pi+Gardener+Dashboard)

## Features

### 🌡️ **Real-time Monitoring**
- Temperature & humidity tracking with 2 DHT sensors
- Individual water level monitoring (3 float sensors)
- Live dashboard with sensor history charts
- 1-minute data logging intervals

### 💡 **Automated Controls**
- **6 Grow Lights**: Schedule-based or manual control
- **5 Hydroponic Pumps**: Cycling operation with adjustable durations
- **2 Circulation Fans**: Air circulation every 30 minutes
- **2 Exhaust Fans**: Temperature/humidity triggered ventilation

### 🛡️ **Safety Features**
- **Fill Timeout Protection**: Prevents flooding (adjustable 5-30 minutes)
- **Overflow Detection**: Emergency shutdown on high water level
- **Reservoir Empty Alerts**: Detects when main water source is depleted
- **Multiple Redundancy**: Hardware and software fail-safes

### 🌐 **Web Interface**
- Responsive dashboard accessible from any device
- Real-time status updates
- Individual component control
- Historical data visualization with Chart.js

## Hardware Requirements

### Core Components
- **Raspberry Pi Zero 2W** (or any Raspberry Pi with GPIO)
- **2x DHT11/DHT22 Temperature & Humidity Sensors**
- **3x Float Sensors** (water level detection)
- **1x Overflow Sensor** (optional, high-level emergency detection)
- **Relays**: 15-channel relay module for controlling:
  - 6x Grow lights
  - 5x Pumps
  - 2x Circulation fans
  - 2x Exhaust fans
  - 1x Water solenoid valve

### GPIO Pin Mapping
```
Grow Lights:     GPIO 6, 7, 8, 9, 20, 21
Pumps:           GPIO 27, 5, 10, 11, 12
Exhaust Fans:    GPIO 13, 16
Circulation Fans: GPIO 19, 26
DHT Sensors:     GPIO 4, 18
Float Sensors:   GPIO 17, 23, 24
Overflow Sensor: GPIO 25
Solenoid Valve:  GPIO 22
```

## Software Requirements

- **Python 3.7+**
- **Raspberry Pi OS** (or any Debian-based Linux)
- **Web Browser** (Chrome, Firefox, Safari, etc.)

## Installation

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/pi-gardener.git
cd pi-gardener
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Hardware Setup
1. Connect all sensors and relays according to the GPIO pin mapping
2. Ensure proper power supplies for relays (separate from Pi's 5V)
3. Test all connections before powering on

### 4. Initial Configuration
```bash
python3 main_controller.py
```
The system will automatically create the database and default settings on first run.

### 5. Access Dashboard
Open your web browser and navigate to:
```
http://<YOUR_PI_IP_ADDRESS>:5000
```

## Configuration

### Default Settings
The system comes pre-configured with sensible defaults:
- **Lights**: 6:00 AM - 10:00 PM schedule
- **Pumps**: 15 min on, 45 min off cycle
- **Fans**: Circulation every 30 min, exhaust when temp >27°C or humidity >65%
- **Safety**: 10-minute fill timeout

### Adjusting Settings
Use the web dashboard to modify:
- Light schedules and modes
- Pump cycle durations
- Fan thresholds and modes
- Safety timeout settings

## Usage

### Starting the System
```bash
python3 main_controller.py
```

### Web Dashboard
- **Live Status**: Current temperature, humidity, and water levels
- **Sensor History**: 20 most recent readings with trend visualization
- **System Controls**: Individual control over all components
- **Safety Monitoring**: Real-time alerts for system issues

### Manual Override
Each component can be set to:
- **Auto**: Follow programmed schedules/logic
- **On**: Force on (manual override)
- **Off**: Force off (manual override)

## Safety Features Explained

### Fill Timeout Protection
Prevents solenoid valve from running indefinitely if a float sensor fails. Adjustable timeout ensures the system won't flood your space.

### Overflow Detection
Hardware backup that immediately shuts off water flow if the overflow sensor detects high water levels.

### Reservoir Empty Detection
If the solenoid runs for the maximum time but water levels don't rise, it indicates the main reservoir is empty, preventing pump damage.

## Troubleshooting

### Common Issues
1. **"table latest_state has no column"** - Delete `hydroponics.db` and restart
2. **Sensor reading failures** - Check DHT sensor connections and GPIO pins
3. **Relay not activating** - Verify relay module power supply
4. **Web interface not loading** - Check firewall settings and port 5000

### Logs
All system events are logged to console. Check for error messages on startup.

## Customization Guide

Pi Gardener is designed to be easily adaptable for different automation projects. Here's how to customize it for your specific needs.

### Hardware Customization

#### Changing GPIO Pins
1. **Update Pin Definitions** in `main_controller.py`:
   ```python
   # Example: Change pump pins
   PUMPS_PINS = [27, 5, 10, 11, 12]  # Your custom pins
   ```

2. **Update GPIO Setup**:
   ```python
   relay_pins = LIGHTS_PINS + PUMPS_PINS + EXHAUST_FANS_PINS + CIRCULATION_FANS_PINS + [SOLENOID_RELAY_PIN]
   for pin in relay_pins:
       GPIO.setup(pin, GPIO.OUT)
       GPIO.output(pin, GPIO.HIGH)
   ```

#### Adding New Sensors
1. **Define New Pins**:
   ```python
   SOIL_MOISTURE_PIN = 14
   ```

2. **Setup GPIO**:
   ```python
   GPIO.setup(SOIL_MOISTURE_PIN, GPIO.IN)
   ```

3. **Add to Control Loop**:
   ```python
   # In run_hardware_loop()
   soil_moisture = GPIO.input(SOIL_MOISTURE_PIN)
   ```

4. **Update Database** (if needed):
   ```python
   cursor.execute('''
   ALTER TABLE sensor_readings ADD COLUMN soil_moisture INTEGER
   ''')
   ```

### Software Customization

#### Adding New Control Logic
1. **Define Component Arrays**:
   ```python
   # Example: Add heaters
   HEATERS_PINS = [15, 18]
   hardware_state["heaters_on"] = [False] * len(HEATERS_PINS)
   ```

2. **Add Control Section**:
   ```python
   # --- Heaters Control ---
   for i, pin in enumerate(HEATERS_PINS):
       mode = app_settings.get(f"heaterMode{i+1}", "auto")
       if mode == "auto":
           should_on = temperature_c < 20.0  # Custom logic
       elif mode == "on":
           should_on = True
       else:
           should_on = False
       toggle_relay(pin, should_on, f"Heater {i+1}")
   ```

#### Custom Settings
1. **Add to Default Settings**:
   ```python
   default_settings = {
       # ... existing settings ...
       "customThreshold": 25.0,
       "customDuration": 300,
   }
   ```

2. **Use in Logic**:
   ```python
   custom_value = app_settings.get("customThreshold", 25.0)
   ```

#### Modifying the Dashboard
1. **Add New Controls** in `dashboard.html`:
   ```html
   <div id="custom-control">
       <h3 class="text-xl font-semibold mb-3">Custom Component</h3>
       <input type="range" id="customSetting" class="setting-input">
   </div>
   ```

2. **Add JavaScript Logic**:
   ```javascript
   // Load setting
   document.getElementById('customSetting').value = settings.customSetting || 25;

   // Save on change
   document.getElementById('customSetting').addEventListener('change', (e) => {
       saveSetting('customSetting', e.target.value);
   });
   ```

### Advanced Customizations

#### Adding New Sensor Types
1. **Install Libraries**:
   ```bash
   pip install new-sensor-library
   ```

2. **Import and Initialize**:
   ```python
   import new_sensor_library
   custom_sensor = new_sensor_library.Sensor(pin)
   ```

3. **Read in Loop**:
   ```python
   custom_reading = custom_sensor.read()
   ```

#### Custom Scheduling
1. **Complex Time Logic**:
   ```python
   from datetime import datetime, time
   import calendar

   def is_seasonal_time():
       month = datetime.now().month
       return month in [6, 7, 8]  # Summer months
   ```

2. **Weather-Based Control** (requires internet):
   ```python
   import requests

   def get_weather():
       response = requests.get('https://api.weatherapi.com/v1/current.json?key=YOUR_KEY&q=YOUR_LOCATION')
       return response.json()['current']['temp_c']
   ```

#### Database Extensions
1. **Add New Tables**:
   ```python
   cursor.execute('''
   CREATE TABLE IF NOT EXISTS custom_events (
       id INTEGER PRIMARY KEY,
       timestamp DATETIME,
       event_type TEXT,
       value REAL
   )
   ''')
   ```

2. **Custom Queries**:
   ```python
   # Add to API endpoints
   @app.route('/api/custom_data')
   def get_custom_data():
       # Your custom logic here
       pass
   ```

### Example: Converting to Aquarium Controller

1. **Change Components**:
   ```python
   # Replace pumps with filters
   FILTERS_PINS = [27, 5, 10, 11, 12]
   # Replace lights with LED strips
   LEDS_PINS = [6, 7, 8, 9, 20, 21]
   # Keep fans for surface agitation
   # Replace solenoid with auto-feeder
   FEEDER_PIN = 22
   ```

2. **Update Settings**:
   ```python
   default_settings = {
       "ledsOnTime": "08:00", "ledsOffTime": "20:00",
       "filterOnDuration": 3600, "filterOffDuration": 60,  # Always on
       "feedInterval": 28800,  # Feed every 8 hours
   }
   ```

3. **Modify Logic**:
   ```python
   # LED control (similar to lights)
   # Filter control (similar to pumps but always on)
   # Auto-feeder logic
   ```

### Best Practices

- **Test Incrementally**: Change one component at a time
- **Backup Database**: Copy `hydroponics.db` before major changes
- **Document Changes**: Update README with your modifications
- **Safety First**: Add appropriate timeouts and fail-safes
- **Power Considerations**: Ensure relay modules have adequate power supplies

### Common Customizations

- **Greenhouse Controller**: Add humidity fans, heaters, shade controls
- **Aquarium System**: Filters, LED lighting, auto-feeders, CO2 injection
- **Terrarium Monitor**: Temperature, humidity, soil moisture sensors
- **Plant Factory**: Multiple light zones, nutrient dosing pumps, pH monitoring

The modular design makes Pi Gardener adaptable to many automation projects beyond hydroponics!

## Development

### Project Structure
```
pi-gardener/
├── main_controller.py    # Main application logic
├── dashboard.html        # Web interface
├── requirements.txt      # Python dependencies
├── hydroponics.db        # SQLite database (auto-created)
└── README.md            # This file
```

### Adding New Features
1. Modify `main_controller.py` for backend logic
2. Update `dashboard.html` for UI changes
3. Test thoroughly with hardware before deploying

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with real hardware
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Check the troubleshooting section
- Ensure all hardware connections are correct

## Disclaimer

This software controls electrical and water systems. Use at your own risk. Always follow local electrical codes and safety practices. The authors are not responsible for any damage or injury caused by improper use.

---

**Happy Gardening! 🌿**