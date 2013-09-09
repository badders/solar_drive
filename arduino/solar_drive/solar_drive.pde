/*
To build this use the Arduino 0017 IDE version

The ethernet library in the IDE needs to be adjusted as per:
http://mcukits.com/2009/04/06/arduino-ethernet-shield-mega-hack/

Also install the Encoder library from:
http://www.pjrc.com/teensy/td_libs_Encoder.html

Implements a driver for the solar telescope that can be communicated with
over ethernet. The arduino has:
 
 ip: 192.168.2.2
 sub: 255.255.255.0
 
 The server listens on port 8010
 
 Control:
 
 No initialisation required. It is up to the calling program to determine how
 the steps and encoder values relate to real-life motion
 
 Commands:
 T - Turn Motor
 Parameters - Motor name, Direction, Number of Turns
 Reply - Integer of encoder count
 
 E - Request Encoder value
 Parameters - Motor name
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
 
 <command><PARAMETERS><newline>
 
 i.e. To turn a motor send:
 
 <command><NAME><direction><no turns><newline character>
 
 Replies with the number of turns counted on the encoder.
 
 i.e. To turn the body 1000 steps send:
 
 'B1000\n'
 
 Then you will recieve a long integer back with the number of steps counted on
 the encoder
 
 A sample session may look like (as python strings):
 
 out: 'R\n'
 out: 'TMC1000\n'
 in:  '200\n'
 out: 'EM\n'
 in: '200\n'
 out: 'TBA300\n'
 in:  '-85\n'
 */

#include "Encoder.h"
#include <Ethernet.h>

#define STEP_DELAY_uS_FAST 50
#define STEP_DELAY_uS_TRACK 1500
#define ENCODER_PAUSE_mS 100
#define SYNC_PAUSE_mS 100

unsigned char mac[] = { 
    0xDE, 0xAD, 0xBE, 0xEF, 0xFE, 0xED };
//the IP address for the shield:
unsigned char ip[] = { 
    192, 168, 2, 2 };
unsigned char subnet[] = {
    255, 255, 255, 0};

typedef struct {
    unsigned int clock;
    unsigned int dir;
    unsigned int sync;
    unsigned int home;
} 
Motor;

Motor m1 = {
    47, 46, 48, 49};
Motor m2 = {
    43, 42, 44, 45};

Encoder e1(20, 21);
Encoder e2(18, 19);

Server server(8010);

char blocking_read(Client &client) {
    char input;
    do {
        input = client.read();
    } 
    while(input == -1);
    return input;
}

unsigned int parse_int(Client &client) {
    char data[10];
    char c;
    int pos = 0;
    do {
        c = blocking_read(client);
        data[pos++] = c; 
    } while (c != '\n');
    data[pos] = (char) NULL;
    return atoi(data);    
}

void encoder_count(Client &client) {
    Encoder *e;
    char mtr = blocking_read(client);

    switch(mtr) {
    case 'M':
        e = &e2;
        break;
    case 'B':
        e = &e1;
        break;
    default:
        Serial.print("Unknown Motor: ");
        Serial.println(mtr);
        return;
    }

    client.println(e->read());
}

void perform_turn(Client &client) {
    Motor *m;
    Encoder *e;

    char mtr = blocking_read(client);

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

    char dir = blocking_read(client);

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

    int steps = parse_int(client);
    int step_delay = STEP_DELAY_uS_TRACK;
    
    if(steps > 100)
        step_delay = STEP_DELAY_uS_FAST;
        
    for(int i=0; i < steps; i++) {
        digitalWrite(m->clock, HIGH);
        delayMicroseconds(step_delay);
        digitalWrite(m->clock, LOW);
        delayMicroseconds(step_delay);
    }

    delay(ENCODER_PAUSE_mS);

    client.println(e->read());

    delay(SYNC_PAUSE_mS);

    digitalWrite(m->sync, HIGH);
}

void setup() {
    Ethernet.begin(mac, ip, subnet);
    server.begin();

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
    Client client = server.available();

    if (client) {
        while (client.available() > 0) {
            char command = blocking_read(client);

            switch(command) {
            case '\n': // Catch any extra newlines
                break;
            case 'R':
                e1.write(0);
                e2.write(0);
                break;
            case 'T':
                perform_turn(client);
                break;
            case 'E':
                encoder_count(client);
                break;
            default:
                Serial.print("Unknown Command: ");
                Serial.println(command);
            }
        }
    }
}



