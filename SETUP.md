# Arcade Card System - Setup Guide

## Quick Start

### Option 1: Simulator (Test Logic Without Hardware)

Run the Python simulator to test the system logic:

```bash
cd /home/stark/arcade-card-system
python3 simulator.py
```

**Features:**
- ✓ Simulate RFID card scans
- ✓ Register new cards
- ✓ Add/deduct credits
- ✓ View balance and transactions
- ✓ Test data loading

### Option 2: Hardware Setup (Full System)

## Prerequisites

### Software Installation

1. **Install PlatformIO (Recommended)**

```bash
# Install PlatformIO via pip
pip install platformio

# Or via VS Code extension
# Install "PlatformIO IDE" extension
```

2. **Install Arduino IDE (Alternative)**

```bash
# Download from: https://www.arduino.cc/en/software
# Install ESP32 board support
# Tools > Board > Boards Manager > "esp32" > Install
```

### Required Arduino Libraries

Install these libraries in your Arduino IDE or PlatformIO:

| Library | Purpose |
|---------|---------|
| MFRC522 | RFID reader control |
| TFT_eSPI | TFT display control |
| ArduinoJson | JSON handling (for data storage) |
| WiFi | WiFi connectivity |

**Install via PlatformIO:** Already configured in `platformio.ini`

**Install via Arduino IDE:**
- Sketch > Include Library > Manage Libraries
- Search and install each library

## Hardware Setup

### Step 1: Gather Components

- [ ] ESP32 DevKit V1
- [ ] RC522 RFID Reader Module
- [ ] 1.8" TFT ST7735 Display 128x160
- [ ] Jumper wires (male-to-female recommended)
- [ ] Breadboard (optional)
- [ ] Mifare RFID cards/tags (13.56MHz)

### Step 2: Wire Components

Follow the wiring diagram in `WIRING.md`

**Critical Connections:**
- RC522 SDA → GPIO 5
- RC522 RST → GPIO 22
- TFT CS → GPIO 15
- TFT DC → GPIO 2
- TFT RESET → GPIO 4
- Shared SPI: SCK→GPIO18, MOSI→GPIO23, MISO→GPIO19

### Step 3: Upload Code

**Via PlatformIO:**
```bash
cd /home/stark/arcade-card-system
pio run --target upload
```

**Via Arduino IDE:**
1. Open `card_kiosk_mvp/card_kiosk_mvp.ino`
2. Select Board: "ESP32 Dev Module"
3. Select Port: Your ESP32's COM port
4. Click Upload

### Step 4: Configure WiFi

Edit the WiFi credentials in the code:
```cpp
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";
```

### Step 5: Test the System

1. Open Serial Monitor (115200 baud)
2. Verify initialization messages:
   ```
   Arcade Card System - Card Kiosk MVP
   =======================================
   RC522 initialized
   TFT initialized
   WiFi connected
   IP address: 192.168.1.100
   ```

3. Scan an RFID card
4. Check TFT display shows card info
5. Press BOOT button (GPIO 0) to add $5 credit

## Using the System

### Card Kiosk Mode

1. **Idle Screen:** Shows "ARCADE CARD KIOSK" - "Scan card to begin"
2. **Card Scanned:**
   - If card exists: Shows UID, owner, balance
   - If new card: Shows "NEW CARD!" then auto-registers as "Guest"
3. **Add Credit:** Press BOOT button to add $5 to current card
4. **Repeat:** System returns to idle after 2 seconds

### Serial Monitor Commands (Planned)

Future versions will support serial commands:
- `BALANCE <UID>` - Check card balance
- `ADD <UID> <amount>` - Add credits
- `DEDUCT <UID> <amount>` - Deduct credits
- `REGISTER <UID> <owner>` - Register new card
- `LIST` - List all cards

## Troubleshooting

### Common Issues

**RC522 not detected:**
- Check SDA (GPIO 5) connection
- Verify SPI wiring (SCK, MOSI, MISO)
- Try 3.3V power instead of 5V

**TFT not displaying:**
- Check CS (GPIO 15), DC (GPIO 2), RESET (GPIO 4)
- Verify TFT library configuration in `User_Setup.h`
- Check power (3.3V)

**Card not reading:**
- Ensure card is compatible (13.56MHz Mifare)
- Check antenna connections
- Try holding card closer (2-5cm)

**WiFi not connecting:**
- Verify SSID and password
- Check 2.4GHz network (not 5GHz)
- Check signal strength

## Next Steps

### Phase 2 Enhancements

- [ ] Add SPIFFS storage for persistent card database
- [ ] Implement button-based credit selection
- [ ] Add transaction logging to SD card
- [ ] Implement cloud sync (WiFi + HTTP API)

### Phase 3: Arcade Machine Integration

- [ ] Create simplified arcade reader code
- [ ] Add REST API for credit verification
- [ ] Implement server-side transaction logging
- [ ] Add multi-machine support

### Phase 4: Full Cloud System

- [ ] PostgreSQL backend
- [ ] Real-time sync
- [ ] Admin dashboard
- [ ] Usage analytics

## Support

Check these files for more details:
- `README.md` - Project overview
- `WIRING.md` - Detailed wiring diagram
- `platformio.ini` - Build configuration
- `simulator.py` - Logic tester

## License

This project is open source. Feel free to modify and use for your arcade!