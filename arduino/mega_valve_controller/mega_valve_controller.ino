// Arduino Mega valve controller for Raspberry Pi over USB serial.
// Protocol (one command per line):
//   PING
//   RESET
//   FIRE <card> <valve> [on_ms] [off_ms]
//
// Example:
//   FIRE 3 7 200 150

#define D0p    22
#define D1p    23
#define D2p    24
#define D3p    25
#define D4p    26
#define D5p    27
#define D6p    28
#define D7p    29
#define STROBE 30
#define MR     31

// If your hardware has card select lines, keep this enabled and set pins below.
// If not, set USE_CARD_SELECT to false and all commands will target the single card.
const bool USE_CARD_SELECT = true;
const int CARD_COUNT = 16;
const int CARD_SELECT_PINS[4] = {32, 33, 34, 35};  // LSB..MSB

const unsigned long DEFAULT_ON_MS = 200;
const unsigned long DEFAULT_OFF_MS = 200;
const unsigned long SERIAL_BAUD = 115200;

String inputLine;

void setValveMask(byte mask) {
  digitalWrite(D0p, (mask >> 0) & 1);
  digitalWrite(D1p, (mask >> 1) & 1);
  digitalWrite(D2p, (mask >> 2) & 1);
  digitalWrite(D3p, (mask >> 3) & 1);
  digitalWrite(D4p, (mask >> 4) & 1);
  digitalWrite(D5p, (mask >> 5) & 1);
  digitalWrite(D6p, (mask >> 6) & 1);
  digitalWrite(D7p, (mask >> 7) & 1);
}

byte valveToMask(int valve) {
  switch (valve) {
    case 1: return 0b10000000;  // D7
    case 2: return 0b00000001;  // D0
    case 3: return 0b01000000;  // D6
    case 4: return 0b00000010;  // D1
    case 5: return 0b00100000;  // D5
    case 6: return 0b00000100;  // D2
    case 7: return 0b00010000;  // D4
    case 8: return 0b00001000;  // D3
    default: return 0;
  }
}

void pulseStrobe() {
  delayMicroseconds(200);
  digitalWrite(STROBE, HIGH);
  delayMicroseconds(200);
  digitalWrite(STROBE, LOW);
}

void resetOutputs() {
  digitalWrite(MR, LOW);
  delayMicroseconds(200);
  digitalWrite(MR, HIGH);
}

bool selectCard(int card) {
  if (card < 1 || card > CARD_COUNT) {
    return false;
  }

  if (!USE_CARD_SELECT) {
    return true;
  }

  int index = card - 1;
  for (int i = 0; i < 4; i++) {
    digitalWrite(CARD_SELECT_PINS[i], (index >> i) & 1);
  }
  delayMicroseconds(200);
  return true;
}

bool fireValve(int card, int valve, unsigned long onMs, unsigned long offMs) {
  if (!selectCard(card)) {
    return false;
  }

  byte mask = valveToMask(valve);
  if (mask == 0) {
    return false;
  }

  setValveMask(mask);
  pulseStrobe();
  delay(onMs);
  resetOutputs();
  delay(offMs);
  return true;
}

void printReady() {
  Serial.println("READY");
  Serial.println("CMDS: PING | RESET | FIRE <card> <valve> [on_ms] [off_ms]");
}

void setup() {
  pinMode(D0p, OUTPUT);
  pinMode(D1p, OUTPUT);
  pinMode(D2p, OUTPUT);
  pinMode(D3p, OUTPUT);
  pinMode(D4p, OUTPUT);
  pinMode(D5p, OUTPUT);
  pinMode(D6p, OUTPUT);
  pinMode(D7p, OUTPUT);
  pinMode(STROBE, OUTPUT);
  pinMode(MR, OUTPUT);

  if (USE_CARD_SELECT) {
    for (int i = 0; i < 4; i++) {
      pinMode(CARD_SELECT_PINS[i], OUTPUT);
      digitalWrite(CARD_SELECT_PINS[i], LOW);
    }
  }

  digitalWrite(STROBE, LOW);
  resetOutputs();

  Serial.begin(SERIAL_BAUD);
  while (!Serial) {
    ;  // Wait for USB serial on boards that support it.
  }

  printReady();
}

void handleCommand(String line) {
  line.trim();
  if (line.length() == 0) {
    return;
  }

  if (line.equalsIgnoreCase("PING")) {
    Serial.println("PONG");
    return;
  }

  if (line.equalsIgnoreCase("RESET")) {
    resetOutputs();
    Serial.println("OK RESET");
    return;
  }

  if (line.startsWith("FIRE ") || line.startsWith("fire ")) {
    int card = -1;
    int valve = -1;
    unsigned long onMs = DEFAULT_ON_MS;
    unsigned long offMs = DEFAULT_OFF_MS;

    char buf[96];
    line.toCharArray(buf, sizeof(buf));

    int count = sscanf(buf, "FIRE %d %d %lu %lu", &card, &valve, &onMs, &offMs);
    if (count < 2) {
      count = sscanf(buf, "fire %d %d %lu %lu", &card, &valve, &onMs, &offMs);
    }

    if (count < 2) {
      Serial.println("ERR BAD_FIRE_FORMAT");
      return;
    }

    if (!fireValve(card, valve, onMs, offMs)) {
      Serial.println("ERR BAD_CARD_OR_VALVE");
      return;
    }

    Serial.print("OK FIRE ");
    Serial.print(card);
    Serial.print(" ");
    Serial.print(valve);
    Serial.print(" ");
    Serial.print(onMs);
    Serial.print(" ");
    Serial.println(offMs);
    return;
  }

  Serial.println("ERR UNKNOWN_CMD");
}

void loop() {
  while (Serial.available() > 0) {
    char c = (char)Serial.read();
    if (c == '\r') {
      continue;
    }
    if (c == '\n') {
      handleCommand(inputLine);
      inputLine = "";
    } else {
      if (inputLine.length() < 90) {
        inputLine += c;
      }
    }
  }
}
