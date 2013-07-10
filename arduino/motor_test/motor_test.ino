
typedef struct {
    unsigned int clock;
    unsigned int dir;
    unsigned int sync;
    unsigned int home;
} Motor;

const Motor m1 = {47, 46, 48, 49};
const Motor m2 = {43, 42, 44, 45};

typedef struct {
    unsigned int index;
    unsigned int A;
    unsigned int B;
} Encoder;

const Encoder e1 = {14, 15, 18};
const Encoder e2 = {19, 20, 21};

volatile unsigned int e1_steps = 0;
volatile unsigned int e2_steps = 0;

void setup() {
    Serial.begin(9600);

    pinMode(m1.clock, OUTPUT);
    pinMode(m1.sync, OUTPUT);
    pinMode(m1.dir, OUTPUT);
    //pinMode(m1pins[m_home_pin], INPUT);

    pinMode(m2.clock, OUTPUT);
    pinMode(m2.sync, OUTPUT);
    pinMode(m2.dir, OUTPUT);
    //pinMode(m2pins[m_home_pin], INPUT);
     
    digitalWrite(m1.sync, HIGH);
    digitalWrite(m2.sync, HIGH);
    Serial.println("Listening for status changes ...");
}

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
 
    digitalWrite(m.sync, HIGH);
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
