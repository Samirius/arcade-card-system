// =============================================================================
// ui.h  --  Operator/player feedback: status LED + buzzer (+ optional display)
// =============================================================================
// Minimal, hardware-light feedback surface driven by the charge state machine.
//   - RGB status LED (3 GPIOs, active-high) OR a single LED as a fallback.
//   - Piezo buzzer on a PWM-capable GPIO (LEDC).
//   - Display is abstracted to printf-style status lines so a TFT/OLED can be
//     dropped in later without touching the state machine. For the scaffold the
//     "display" is the serial console.
// =============================================================================
#pragma once

#include <Arduino.h>

enum class UiState {
    Boot,          // powering up
    Idle,          // ready, waiting for a tap
    Reading,       // card detected, working
    ChargingOnline,// contacting cloud
    ApprovedOnline,// server approved
    ApprovedOffline,// authorized locally within envelope caps
    Declined,      // server/local decline (insufficient funds, cap, etc.)
    OfflineNoCaps, // offline and no valid envelope -> cannot authorize
    Error,         // network/HW/protocol error
    Syncing        // uploading reconcile batch
};

namespace ui {

void begin();

// Set the high-level state; drives LED colour + a short buzzer motif.
void setState(UiState s);

// Push a status line to the display/console (top line = title, bottom = detail).
void showLines(const String& title, const String& detail);

// Convenience one-liners for the common terminal states.
void beepApprove();
void beepDecline();
void beepError();

// Call frequently from loop(); handles non-blocking LED blink timing.
void tick();

}  // namespace ui
