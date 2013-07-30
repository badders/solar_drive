#include "Encoder.h"

#define STEP_DELAY_uS 100
#define ENCODER_PAUSE_mS 100

typedef struct {
    unsigned int clock;
    unsigned int dir;
    unsigned int sync;
    unsigned int home;
} Motor;

const Motor m1 = {47, 46, 48, 49};
const Motor m2 = {43, 42, 44, 45};

Encoder e1(18, 19);
Encoder e2(20, 21);

void turn(unsigned int motor, unsigned int direct, unsigned int steps) {
    Motor m;

    if(motor == 1) {
        m = m1;
    } else {
        m = m2;
    }

    digitalWrite(m.sync, LOW);

    Serial.print("Turning Motor ");
    Serial.print(motor);
    Serial.print(" for ");
    Serial.print(steps);
    Serial.println(" steps.");

    if(direct == 1) {
        digitalWrite(m.dir, HIGH);
    } else {
        digitalWrite(m.dir, LOW);
    }

    for(int i=0; i < steps; i++) {
        digitalWrite(m.clock, HIGH);
        delayMicroseconds(STEP_DELAY_uS);
        digitalWrite(m.clock, LOW);
        delayMicroseconds(STEP_DELAY_uS);
    }

    delay(ENCODER_PAUSE_mS);

    Serial.print("Encoder 1: ");
    Serial.println(e1.read());
    Serial.print("Encoder 2: ");
    Serial.println(e2.read());

    digitalWrite(m.sync, HIGH);
}

void setup() {
    Serial.begin(9600);

    pinMode(m1.clock, OUTPUT);
    pinMode(m1.sync, OUTPUT);
    pinMode(m1.dir, OUTPUT);
    pinMode(m1.home, INPUT);

    pinMode(m2.clock, OUTPUT);
    pinMode(m2.sync, OUTPUT);
    pinMode(m2.dir, OUTPUT);
    pinMode(m2.home, INPUT);

    e1.write(0);
    e2.write(0);

    digitalWrite(m1.sync, HIGH);
    digitalWrite(m2.sync, HIGH);

    Serial.println("Listening for status changes ...");
}

void loop() {
    int motor, direct, steps;
    while (Serial.available() > 0) {
        motor = Serial.parseInt();
        direct = Serial.parseInt();
        steps = Serial.parseInt();

        if(Serial.read() == '\n') {
            turn(motor, direct, steps);
        }

        Serial.println("Finished Turning");
    }
}
