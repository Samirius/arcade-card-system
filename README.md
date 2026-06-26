# Arcade Card System

A modern Intercard-style credit system for arcades with local + cloud sync.

## Hardware

- ESP32
- RC522 RFID Reader (13.56MHz)
- 1.8" TFT Display 128x160 (ST7735, SPI)

## Pin Configuration

### RC522 (SPI)
```
SDA (SS)  → GPIO 5
SCK       → GPIO 18
MOSI      → GPIO 23
MISO      → GPIO 19
RST       → GPIO 22
3.3V      → 3.3V
GND       → GND
```

### TFT ST7735 (SPI)
```
CS        → GPIO 15
DC (RS)   → GPIO 2
RESET     → GPIO 4
MOSI      → GPIO 23 (shared with RC522)
SCK       → GPIO 18 (shared with RC522)
MISO      → GPIO 19 (shared with RC522)
VCC       → 3.3V
GND       → GND
LED       → 3.3V
```

### Buttons (Optional)
```
Add Credit → GPIO 0 (ESP32 boot button) or GPIO 14
New Card   → GPIO 14 (or separate button)
```

## Features

- [x] RFID card reading
- [x] Balance display on TFT
- [x] Add credits to card
- [x] Register new cards
- [ ] Local storage (SPIFFS/SD)
- [ ] Cloud sync (WiFi + PostgreSQL)
- [ ] Arcade machine integration
- [ ] Transaction logging

## Phase 1: Card Kiosk MVP

Current focus: Basic card read + balance display + admin credit management.

## Next Steps

1. Set up Arduino/PlatformIO project
2. Implement RFID reader
3. Implement TFT display
4. Add local card database
5. Create admin interface
6. Add WiFi sync capabilities