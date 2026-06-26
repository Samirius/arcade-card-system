/*
 * Arcade Card System - Card Kiosk MVP
 * Hardware: ESP32 + RC522 + ST7735 TFT 128x160
 *
 * Features:
 * - Read RFID cards
 * - Display card balance on TFT
 * - Add credits to cards
 * - Register new cards
 */

#include <SPI.h>
#include <WiFi.h>
#include <MFRC522.h>
#include <TFT_eSPI.h>

// RC522 Pins
#define RST_PIN 22
#define SS_PIN 5

// Button Pins
#define BTN_ADD_CREDIT 0  // ESP32 boot button
#define BTN_NEW_CARD 14

// TFT Display (ST7735)
TFT_eSPI tft = TFT_eSPI();

// RFID Reader
MFRC522 mfrc522(SS_PIN, RST_PIN);

// WiFi Credentials (placeholder - update these)
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// Card Database (in-memory for now, will move to SPIFFS)
struct Card {
  String uid;
  float balance;
  String owner;
};

Card cards[50];  // Max 50 cards
int cardCount = 0;

// Display states
enum DisplayState {
  STATE_IDLE,
  STATE_CARD_DETECTED,
  STATE_ADD_CREDIT,
  STATE_NEW_CARD
};

DisplayState currentState = STATE_IDLE;
String currentCardUID = "";
float currentCardBalance = 0.0;

// Debounce variables
unsigned long lastCardRead = 0;
const unsigned long CARD_READ_DELAY = 2000;  // 2 seconds between reads

void setup() {
  Serial.begin(115200);
  Serial.println("Arcade Card System - Card Kiosk MVP");
  Serial.println("=======================================");

  // Initialize SPI
  SPI.begin();

  // Initialize RFID
  mfrc522.PCD_Init();
  Serial.println("RC522 initialized");

  // Initialize TFT
  tft.init();
  tft.setRotation(1);  // Landscape
  tft.fillScreen(ST7735_BLACK);
  Serial.println("TFT initialized");

  // Initialize buttons
  pinMode(BTN_ADD_CREDIT, INPUT_PULLUP);
  pinMode(BTN_NEW_CARD, INPUT_PULLUP);

  // Connect to WiFi
  connectWiFi();

  // Load existing cards from SPIFFS (placeholder)
  // loadCards();

  // Show idle screen
  showIdleScreen();
}

void loop() {
  checkRFID();
  checkButtons();
}

void checkRFID() {
  // Prevent reading same card too quickly
  if (millis() - lastCardRead < CARD_READ_DELAY) {
    return;
  }

  if (!mfrc522.PICC_IsNewCardPresent() || !mfrc522.PICC_ReadCardSerial()) {
    return;
  }

  // Read card UID
  String uid = getCardUID();
  Serial.println("Card detected: " + uid);

  lastCardRead = millis();

  // Check if card exists
  int cardIndex = findCardIndex(uid);

  if (cardIndex != -1) {
    // Card exists - show balance
    currentCardUID = uid;
    currentCardBalance = cards[cardIndex].balance;
    currentState = STATE_CARD_DETECTED;
    showCardInfo(uid, cards[cardIndex].balance, cards[cardIndex].owner);
  } else {
    // New card
    currentCardUID = uid;
    currentCardBalance = 0.0;
    currentState = STATE_NEW_CARD;
    showNewCardScreen(uid);
  }

  mfrc522.PICC_HaltA();
}

void checkButtons() {
  if (currentState == STATE_CARD_DETECTED) {
    // Add credit button
    if (digitalRead(BTN_ADD_CREDIT) == LOW) {
      delay(200);  // Debounce
      if (digitalRead(BTN_ADD_CREDIT) == LOW) {
        addCreditToCard(currentCardUID);
      }
    }
  }
}

String getCardUID() {
  String uid = "";
  for (byte i = 0; i < mfrc522.uid.size; i++) {
    uid += String(mfrc522.uid.uidByte[i] < 0x10 ? "0" : "");
    uid += String(mfrc522.uid.uidByte[i], HEX);
  }
  uid.toUpperCase();
  return uid;
}

int findCardIndex(String uid) {
  for (int i = 0; i < cardCount; i++) {
    if (cards[i].uid == uid) {
      return i;
    }
  }
  return -1;
}

void addCreditToCard(String uid) {
  float amount = 5.0;  // Default: add $5

  int cardIndex = findCardIndex(uid);
  if (cardIndex != -1) {
    cards[cardIndex].balance += amount;
    currentCardBalance = cards[cardIndex].balance;
    Serial.println("Added $" + String(amount) + " to card " + uid);
    Serial.println("New balance: $" + String(cards[cardIndex].balance));

    // Update display
    showCardInfo(uid, cards[cardIndex].balance, cards[cardIndex].owner);
    delay(2000);
  }
}

void registerNewCard(String uid, String owner) {
  if (cardCount < 50) {
    cards[cardCount].uid = uid;
    cards[cardCount].balance = 0.0;
    cards[cardCount].owner = owner;
    cardCount++;

    Serial.println("Registered new card: " + uid);
    Serial.println("Owner: " + owner);

    // Save to SPIFFS (placeholder)
    // saveCards();

    showCardInfo(uid, 0.0, owner);
  }
}

void connectWiFi() {
  Serial.print("Connecting to WiFi");
  WiFi.begin(ssid, password);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi connected");
    Serial.println("IP address: " + WiFi.localIP().toString());
  } else {
    Serial.println("\nWiFi connection failed - running offline");
  }
}

// ============ DISPLAY FUNCTIONS ============

void showIdleScreen() {
  tft.fillScreen(ST7735_BLACK);
  tft.setTextColor(ST7735_WHITE, ST7735_BLACK);
  tft.setTextSize(2);
  tft.setCursor(10, 20);
  tft.print("ARCADE");
  tft.setCursor(10, 45);
  tft.print("CARD");
  tft.setCursor(10, 70);
  tft.print("KIOSK");

  tft.setTextSize(1);
  tft.setCursor(5, 110);
  tft.print("Scan card to begin");

  tft.setTextColor(ST7735_GREEN, ST7735_BLACK);
  tft.setCursor(5, 140);
  tft.print("Online");
}

void showCardInfo(String uid, float balance, String owner) {
  tft.fillScreen(ST7735_BLACK);

  tft.setTextColor(ST7735_CYAN, ST7735_BLACK);
  tft.setTextSize(1);
  tft.setCursor(5, 5);
  tft.print("CARD ID:");

  tft.setTextColor(ST7735_WHITE, ST7735_BLACK);
  tft.setCursor(5, 20);
  tft.print(uid);

  tft.setTextColor(ST7735_YELLOW, ST7735_BLACK);
  tft.setCursor(5, 45);
  tft.print("BALANCE:");

  tft.setTextColor(ST7735_GREEN, ST7735_BLACK);
  tft.setTextSize(2);
  tft.setCursor(5, 60);
  tft.print("$");
  tft.print(balance, 2);

  tft.setTextSize(1);
  tft.setTextColor(ST7735_CYAN, ST7735_BLACK);
  tft.setCursor(5, 90);
  tft.print("OWNER:");
  tft.setCursor(5, 105);
  tft.setTextColor(ST7735_WHITE, ST7735_BLACK);
  tft.print(owner);

  tft.setTextColor(ST7735_MAGENTA, ST7735_BLACK);
  tft.setCursor(5, 130);
  tft.print("Press BOOT to add");
  tft.setCursor(5, 145);
  tft.print("$5 credit");
}

void showNewCardScreen(String uid) {
  tft.fillScreen(ST7735_BLACK);

  tft.setTextColor(ST7735_YELLOW, ST7735_BLACK);
  tft.setTextSize(1);
  tft.setCursor(5, 5);
  tft.print("NEW CARD!");

  tft.setTextColor(ST7735_CYAN, ST7735_BLACK);
  tft.setCursor(5, 30);
  tft.print("CARD ID:");

  tft.setTextColor(ST7735_WHITE, ST7735_BLACK);
  tft.setCursor(5, 45);
  tft.print(uid);

  tft.setTextColor(ST7735_GREEN, ST7735_BLACK);
  tft.setCursor(5, 80);
  tft.print("Register via");

  tft.setTextColor(ST7735_WHITE, ST7735_BLACK);
  tft.setCursor(5, 95);
  tft.print("Serial Monitor");

  // Auto-register with "Guest" after 3 seconds
  delay(3000);
  registerNewCard(uid, "Guest");
}