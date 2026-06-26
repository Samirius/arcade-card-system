# Wiring Diagram - Arcade Card System

## ESP32 Pin Configuration

### RC522 RFID Reader (SPI Connection)

```
RC522 Pin    →    ESP32 Pin    →    Notes
─────────────────────────────────────────────────────
SDA (SS)     →    GPIO 5       →    Chip Select
SCK          →    GPIO 18      →    SPI Clock
MOSI         →    GPIO 23      →    Master Out Slave In
MISO         →    GPIO 19      →    Master In Slave Out
RST          →    GPIO 22      →    Reset
3.3V         →    3.3V         →    Power
GND          →    GND          →    Ground
```

### TFT ST7735 Display 128x160 (SPI Connection)

```
TFT Pin      →    ESP32 Pin    →    Notes
─────────────────────────────────────────────────────
CS           →    GPIO 15      →    Chip Select
DC (RS)      →    GPIO 2       →    Data/Command
RESET        →    GPIO 4       →    Reset
LED          →    3.3V         →    Backlight (optional)
MOSI         →    GPIO 23      →    Shared with RC522
SCK          →    GPIO 18      →    Shared with RC522
MISO         →    GPIO 19      →    Shared with RC522
VCC          →    3.3V         →    Power
GND          →    GND          →    Ground
```

### Buttons (Optional - For Admin Functions)

```
Button       →    ESP32 Pin    →    Notes
─────────────────────────────────────────────────────
Add Credit   →    GPIO 0       →    ESP32 Boot Button (pull-down)
New Card     →    GPIO 14      →    External button (pull-up)
```

**Button Wiring:**
- Connect button between GPIO pin and GND
- Use INPUT_PULLUP in code (button connects to GND when pressed)
- For GPIO 0 (boot button): Already has pull-up on ESP32 board

## Physical Connection Diagram

```
                    ┌─────────────────┐
                    │      ESP32      │
                    │  (DevKit V1)    │
                    └──────┬────┬─────┘
                           │    │
         ┌─────────────────┴────┴─────────────────┐
         │                   │                    │
         ▼                   ▼                    ▼
    ┌─────────┐         ┌─────────┐         ┌─────────┐
    │  RC522  │         │  ST7735 │         │ Buttons │
    │ RFID    │         │  TFT    │         │         │
    └─────────┘         └─────────┘         └─────────┘
```

## Shared SPI Bus

**Important:** RC522 and TFT share the SPI bus (SCK, MOSI, MISO).
Each device has its own Chip Select (CS) pin:
- RC522: GPIO 5
- TFT: GPIO 15

This allows the ESP32 to communicate with both devices independently.

## Power Considerations

- **Voltage:** 3.3V only (ESP32 is NOT 5V tolerant)
- **Current:** ESP32 + RC522 + TFT ≈ 150-200mA
- **Power Source:** USB or 5V adapter with 3.3V regulator recommended

## Testing Checklist

### Hardware Test
- [ ] Verify all connections match diagram
- [ ] Check for loose wires
- [ ] Ensure proper voltage (3.3V)
- [ ] Verify SPI pins are correct

### Software Test
- [ ] Upload code to ESP32
- [ ] Open Serial Monitor (115200 baud)
- [ ] Check initialization messages
- [ ] Verify WiFi connection (if configured)
- [ ] Test RFID card scan
- [ ] Check TFT display
- [ ] Test button functionality

## Troubleshooting

### RC522 Not Detected
- Check SDA (SS) pin (GPIO 5)
- Verify SPI connections (SCK, MOSI, MISO)
- Check 3.3V power supply
- Try different RC522 module

### TFT Not Displaying
- Check CS pin (GPIO 15)
- Verify DC and RESET pins
- Check TFT library configuration
- Try increasing SPI frequency

### RFID Not Reading Cards
- Check card is compatible (13.56MHz Mifare)
- Verify antenna connections
- Check distance (should be 2-5cm)
- Try different cards

### WiFi Not Connecting
- Verify SSID and password
- Check WiFi signal strength
- Try 2.4GHz network (ESP32 doesn't support 5GHz)