/*
Implements a driver for the solar telescope that can be communicated with
over serial

Control:

No initialisation required. It is up to the calling program to determine how
the steps and encoder values relate to real-life motion

Commands:
T - Turn Motor
    Reply - Integer of encoder count
R - Reset encoder counts to 0
    Reply - None

Motor names:
B - Main body motor
M - Mirror Motor

Directions:
C - Clockwise
A - Anticlockwise

Protocol:

<command> <PARAMETERS><newline>

i.e. To turn a motor send:

<command> <NAME> <direction> <no turns><newline character>

Replies with the number of turns counted on the encoder.

i.e. To turn the body 1000 steps send:

'B1000\n'

Then you will recieve a long integer back with the number of steps counted on
the encoder

A sample session may look like (as python strings):

out: 'R\n'
out: 'T MC 1000\n'
in:  '200\n'
out: 'T BA 300\n'
in:  '-85\n'
*/

#include "Encoder.h"

#define STEP_DELAY_uS 50
#define ENCODER_PAUSE_mS 100
#define SYNC_PAUSE_mS 100


//#define DEBUG

#ifdef DEBUG
#warning "DEBUG is defined!"
#endif

typedef struct {
    unsigned int clock;
    unsigned int dir;
    unsigned int sync;
    unsigned int home;
} Motor;

Motor m1 = {47, 46, 48, 49};
Motor m2 = {43, 42, 44, 45};

Encoder e1(20, 21);
Encoder e2(18, 19);

char blocking_read() {
    char input;
    do {
        input = Serial.read();
    } while(input == -1);
    return input;
}

void perform_turn() {
    Motor *m;
    Encoder *e;

    char mtr = blocking_read();

#ifdef DEBUG
    Serial.print("MOTOR: ");
    Serial.println(mtr);
#endif

    switch(mtr) {
    case 'M':
        m = &m2;
        e = &e2;
        break;
    case 'B':
        m = &m1;
        e = &e1;
        break;
    default:
        Serial.print("Unknown Motor: ");
        Serial.println(mtr);
        return;
    }

    digitalWrite(m->sync, LOW);
    delay(SYNC_PAUSE_mS);

    char dir = blocking_read();

#ifdef DEBUG
    Serial.print("DIRECTION: ");
    Serial.println(dir);
#endif

    switch(dir) {
    case 'A':
        digitalWrite(m->dir, LOW);
        break;
    case 'C':
        digitalWrite(m->dir, HIGH);
        break;
    default:
        Serial.println("Unknown Direction");
        return;
    }

    int steps = Serial.parseInt();

    for(int i=0; i < steps; i++) {
        digitalWrite(m->clock, HIGH);
        delayMicroseconds(STEP_DELAY_uS);
        digitalWrite(m->clock, LOW);
        delayMicroseconds(STEP_DELAY_uS);
    }

    delay(ENCODER_PAUSE_mS);

    Serial.println(e->read());

    delay(SYNC_PAUSE_mS);

    digitalWrite(m->sync, HIGH);
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
}

void loop() {
    while (Serial.available() > 0) {
        char command = blocking_read();

#ifdef DEBUG
        Serial.print("COMMAND: ");
        Serial.println(command);
#endif

        switch(command) {
        case 'R':
            e1.write(0);
            e2.write(0);
            break;
        case 'T':
            perform_turn();
            break;
        default:
            Serial.print("Unknown Command: ");
            Serial.println(command);
        }
        blocking_read();
    }
}
