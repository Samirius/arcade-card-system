// =============================================================================
// ui.cpp
// =============================================================================
#include "ui.h"

// ---- Pin map (see README wiring table) -------------------------------------
#define PIN_LED_R   25
#define PIN_LED_G   26
#define PIN_LED_B   27
#define PIN_BUZZER  32

// LEDC (ESP32 PWM) channel for the buzzer tone.
#define BUZZER_LEDC_CH   0

namespace {
UiState  g_state = UiState::Boot;
bool     g_blinkOn = false;
uint32_t g_lastBlink = 0;

void setRGB(bool r, bool g, bool b) {
    digitalWrite(PIN_LED_R, r ? HIGH : LOW);
    digitalWrite(PIN_LED_G, g ? HIGH : LOW);
    digitalWrite(PIN_LED_B, b ? HIGH : LOW);
}

// Named buzz() (not tone()) to avoid clashing with Arduino's global tone().
void buzz(uint32_t freq, uint32_t ms) {
    ledcWriteTone(BUZZER_LEDC_CH, freq);
    delay(ms);
    ledcWriteTone(BUZZER_LEDC_CH, 0);
}
}  // namespace

namespace ui {

void begin() {
    pinMode(PIN_LED_R, OUTPUT);
    pinMode(PIN_LED_G, OUTPUT);
    pinMode(PIN_LED_B, OUTPUT);
    setRGB(false, false, false);

    ledcSetup(BUZZER_LEDC_CH, 2000, 8);
    ledcAttachPin(PIN_BUZZER, BUZZER_LEDC_CH);
    ledcWriteTone(BUZZER_LEDC_CH, 0);

    setState(UiState::Boot);
}

void beepApprove() { buzz(1200, 80); buzz(1800, 120); }
void beepDecline() { buzz(400, 250); }
void beepError()   { buzz(300, 120); delay(60); buzz(300, 120); }

void showLines(const String& title, const String& detail) {
    // Serial stands in for a TFT/OLED in the scaffold.
    Serial.print(F("[UI] "));
    Serial.print(title);
    if (detail.length()) {
        Serial.print(F(" | "));
        Serial.print(detail);
    }
    Serial.println();
}

void setState(UiState s) {
    g_state = s;
    switch (s) {
        case UiState::Boot:            setRGB(false, false, true);  break; // blue
        case UiState::Idle:            setRGB(false, true,  false); break; // green (blinks)
        case UiState::Reading:         setRGB(false, true,  true);  break; // cyan
        case UiState::ChargingOnline:  setRGB(false, false, true);  break; // blue
        case UiState::Syncing:         setRGB(true,  false, true);  break; // magenta
        case UiState::ApprovedOnline:  setRGB(false, true,  false); beepApprove(); break;
        case UiState::ApprovedOffline: setRGB(true,  true,  false); beepApprove(); break; // yellow
        case UiState::Declined:        setRGB(true,  false, false); beepDecline(); break;
        case UiState::OfflineNoCaps:   setRGB(true,  false, false); beepError();   break;
        case UiState::Error:           setRGB(true,  false, false); beepError();   break;
    }
}

void tick() {
    // Gentle idle heartbeat blink so the operator knows the reader is alive.
    if (g_state != UiState::Idle) return;
    uint32_t now = millis();
    if (now - g_lastBlink >= 1000) {
        g_lastBlink = now;
        g_blinkOn = !g_blinkOn;
        setRGB(false, g_blinkOn, false);
    }
}

}  // namespace ui
