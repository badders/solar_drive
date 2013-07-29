
typedef struct {
    unsigned int clock;
    unsigned int dir;
    unsigned int sync;
    unsigned int home;
} Motor;

const Motor m1 = {47, 46, 48, 49};
const Motor m2 = {43, 42, 44, 45};

typedef struct {
    unsigned int Z;
    unsigned int A;
    unsigned int B;
} Encoder;

const Encoder e1 = {2, 18, 19};
const Encoder e2 = {3, 20, 21};

volatile long e1_steps = 0;
volatile long e2_steps = 0;

void motor_step(unsigned int pin) {
    digitalWrite(pin, HIGH);
    delayMicroseconds(50);
    digitalWrite(pin, LOW);
    delayMicroseconds(50);
}

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
        delayMicroseconds(50);
        digitalWrite(m.clock, LOW);
        delayMicroseconds(50);
    }

    delay(10);
    Serial.print("Encoder 1: ");
    Serial.println(e1_steps);
    Serial.print("Encoder 2: ");
    Serial.println(e2_steps);

    digitalWrite(m.sync, HIGH);
}

void doEncode1() {
    int A = digitalRead(e1.A);
    int B = digitalRead(e1.B);

    e1_steps += A == B ? 1 : -1;
}

void doEncode2() {
    int A = digitalRead(e2.A);
    int B = digitalRead(e2.B);

    e2_steps += A == B ? 1 : -1;
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

    pinMode(e1.Z, INPUT);
    pinMode(e1.A, INPUT);
    pinMode(e1.B, INPUT);

    pinMode(e2.Z, INPUT);
    pinMode(e2.A, INPUT);
    pinMode(e2.B, INPUT);

    digitalWrite(m1.sync, HIGH);
    digitalWrite(m2.sync, HIGH);

    attachInterrupt(0, doEncode1, CHANGE);
    attachInterrupt(1, doEncode2, CHANGE);

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
