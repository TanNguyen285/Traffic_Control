// =============================================================
// FINAL CLEAN VERSION
// Traffic FSM + UART + Reset + Turbo
// Two 7-seg Modules (each 2-digit via 2x74HC595)
// Serial ONLY:
//   - "yell"
//   - "[RX] m1~m4"
//   - "==============="
//   - "[APPLY] Applying Mx"
//   - "[DEFAULT] no response, use default timing"
// =============================================================

#include <Ticker.h>

Ticker clk;
volatile bool clk_flag = false;
void onTick() { clk_flag = true; }

// =============================================================
// UART CONFIG
// =============================================================
int pending_level = -1;
bool system_ready = false;

// =============================================================
// RESET BUTTON
// =============================================================
const int RESET_BTN = 21;
int reset_state = HIGH, last_reset_state = HIGH;
unsigned long reset_last_time = 0;
const int debounce_delay = 40;

// =============================================================
// SPEED BUTTON (TURBO)
// =============================================================
int tick_per_second_normal = 20;
int tick_per_second_turbo  = 3;
int tick_per_second_current = 20;

// =============================================================
// FSM CONFIG
// =============================================================
enum State {
  RED1_GREEN2,
  RED1_YELLOW2,
  GREEN1_RED2,
  YELLOW1_RED2
};

State current = RED1_GREEN2;
void enter_state(State s);

// =============================================================
// TIMING CONFIG
// =============================================================
int RED_TIME[4]   = {20, 45, 60, 90};
int GREEN_TIME[4] = {17, 42, 57, 87};
const int YELLOW_TIME = 3;

int RED_DEFAULT   = 30;
int GREEN_DEFAULT = 27;

int level = 0;
int c1_left = 0;
int c2_left = 0;

// =============================================================
// TICK
// =============================================================
int tick_ms = 50;
int tick_counter = 0;

// =============================================================
// TRAFFIC LED PINS
// =============================================================
const int T1_RED = 17, T1_YELLOW = 4, T1_GREEN = 16;
const int T2_RED = 32, T2_YELLOW = 25, T2_GREEN = 33;

// =============================================================
// 7-SEG PINS
// =============================================================
const int SEG1_DATA = 5, SEG1_CLK = 18, SEG1_LATCH = 19;
const int SEG2_DATA = 27, SEG2_CLK = 26, SEG2_LATCH = 14;

// =============================================================
// 7-SEG CODE (COMMON CATHODE → INVERTED WHEN SEND)
// =============================================================
byte segCode[10] = {
  0x3F, 0x06, 0x5B, 0x4F, 0x66,
  0x6D, 0x7D, 0x07, 0x7F, 0x6F
};

// =============================================================
// UART HELPERS
// =============================================================
void send_initial_yell() {
  Serial.println("yell");
  pending_level = -1;
  system_ready = false;
}

void uart_check() {
  if (!Serial.available()) return;

  String r = Serial.readStringUntil('\n');
  r.trim();

  Serial.printf("[RX] %s\n", r.c_str());

  if      (r == "m1") pending_level = 0;
  else if (r == "m2") pending_level = 1;
  else if (r == "m3") pending_level = 2;
  else if (r == "m4") pending_level = 3;
  else return;

  Serial.println("========================");
}

// =============================================================
// BUTTONS
// =============================================================
void check_reset_button() {
  int reading = digitalRead(RESET_BTN);
  if (reading != last_reset_state) reset_last_time = millis();

  if (millis() - reset_last_time > debounce_delay) {
    if (reading != reset_state) {
      reset_state = reading;
      if (reset_state == LOW) send_initial_yell();
    }
  }
  last_reset_state = reading;
}

// =============================================================
// DISPLAY
// =============================================================
void displayTwoDigit(int dataPin, int clockPin, int latchPin, int value) {
  if (value < 0) value = 0;
  if (value > 99) value %= 100;

  int tens = value / 10;
  int units = value % 10;

  digitalWrite(latchPin, LOW);
  shiftOut(dataPin, clockPin, MSBFIRST, (byte)~segCode[units]);
  shiftOut(dataPin, clockPin, MSBFIRST, (byte)~segCode[tens]);
  digitalWrite(latchPin, HIGH);
}

void update_display() {
  displayTwoDigit(SEG1_DATA, SEG1_CLK, SEG1_LATCH, c1_left);
  displayTwoDigit(SEG2_DATA, SEG2_CLK, SEG2_LATCH, c2_left);
}

// =============================================================
// TRAFFIC LEDS
// =============================================================
void update_traffic_leds() {
  digitalWrite(T1_RED,    current == RED1_GREEN2 || current == RED1_YELLOW2);
  digitalWrite(T1_YELLOW, current == YELLOW1_RED2);
  digitalWrite(T1_GREEN,  current == GREEN1_RED2);

  digitalWrite(T2_RED,    current == GREEN1_RED2 || current == YELLOW1_RED2);
  digitalWrite(T2_YELLOW, current == RED1_YELLOW2);
  digitalWrite(T2_GREEN,  current == RED1_GREEN2);
}

// =============================================================
// FSM
// =============================================================
void fsm_tick_second() {

  uart_check();

  // --- INIT WAIT ---
  if (!system_ready && pending_level != -1) {
    level = pending_level;
    system_ready = true;
    enter_state(RED1_GREEN2);
    return;
  }
  if (!system_ready) return;

  if (c1_left > 0) c1_left--;
  if (c2_left > 0) c2_left--;

  if (current == RED1_GREEN2 && c2_left == 0)
    enter_state(RED1_YELLOW2);

  else if (current == RED1_YELLOW2 && c2_left == 0)
    enter_state(GREEN1_RED2);

  else if (current == GREEN1_RED2 && c1_left == 0) {
    Serial.println("yell");
    pending_level = -1;
    enter_state(YELLOW1_RED2);
  }

  else if (current == YELLOW1_RED2 && c1_left == 0) {

    if (pending_level == -1) {
      Serial.println("[DEFAULT] no response, use default timing");
      RED_TIME[level]   = RED_DEFAULT;
      GREEN_TIME[level] = GREEN_DEFAULT;
    } else {
      level = pending_level;
      Serial.printf("[APPLY] Applying M%d\n", level + 1);
    }

    pending_level = -1;
    enter_state(RED1_GREEN2);
  }

  update_display();
  update_traffic_leds();
}

// =============================================================
// ENTER STATE
// =============================================================
void enter_state(State s) {
  current = s;

  if (s == RED1_GREEN2) {
    c1_left = RED_TIME[level];
    c2_left = GREEN_TIME[level];
  }
  else if (s == RED1_YELLOW2) c2_left = YELLOW_TIME;
  else if (s == GREEN1_RED2) {
    c1_left = GREEN_TIME[level];
    c2_left = RED_TIME[level];
  }
  else if (s == YELLOW1_RED2) c1_left = YELLOW_TIME;
}

// =============================================================
// SETUP / LOOP
// =============================================================
void setup() {
  Serial.begin(115200);

  pinMode(RESET_BTN, INPUT_PULLUP);

  pinMode(T1_RED, OUTPUT); pinMode(T1_YELLOW, OUTPUT); pinMode(T1_GREEN, OUTPUT);
  pinMode(T2_RED, OUTPUT); pinMode(T2_YELLOW, OUTPUT); pinMode(T2_GREEN, OUTPUT);

  pinMode(SEG1_DATA, OUTPUT); pinMode(SEG1_CLK, OUTPUT); pinMode(SEG1_LATCH, OUTPUT);
  pinMode(SEG2_DATA, OUTPUT); pinMode(SEG2_CLK, OUTPUT); pinMode(SEG2_LATCH, OUTPUT);

  clk.attach_ms(tick_ms, onTick);
  send_initial_yell();
}

void loop() {
  check_reset_button();

  if (!clk_flag) return;
  clk_flag = false;

  if (++tick_counter >= tick_per_second_current) {
    tick_counter = 0;
    fsm_tick_second();
  }
}
