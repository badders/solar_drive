int clock_pin = 1;
int dir_pin = 0;
int sync_pin = 2;
int home_pin = 3;

int m1pins[] = {46, 47, 48, 49};
int m2pins[] = {42, 43, 44, 45};

void setup() {
    Serial.begin(9600);

    pinMode(m1pins[clock_pin], OUTPUT);
    pinMode(m1pins[sync_pin], OUTPUT);
    pinMode(m1pins[dir_pin], OUTPUT);
    //pinMode(m1pins[home_pin], INPUT);

    pinMode(m2pins[clock_pin], OUTPUT);
    pinMode(m2pins[sync_pin], OUTPUT);
    pinMode(m2pins[dir_pin], OUTPUT);
    //pinMode(m2pins[home_pin], INPUT);
     
    digitalWrite(m1pins[sync_pin], HIGH);
    digitalWrite(m2pins[sync_pin], HIGH);
    digitalWrite(m2pins[dir_pin], LOW);
    digitalWrite(m1pins[dir_pin], LOW);
    Serial.println("Listening for status changes ...");
}

void motor_step(int *m) {
    digitalWrite(m[clock_pin], HIGH);
    delayMicroseconds(50);
    digitalWrite(m[clock_pin], LOW);
    delayMicroseconds(50);
}

void turn(int motor, int direct, int steps) {
    int *m;
  
    if(motor == 1) {
        m = m1pins;
    } else {
        m = m2pins;
    }
  
    digitalWrite(m[sync_pin], LOW);
    
    Serial.print("Turning Motor ");
    Serial.print(motor);
    Serial.print(" for ");
    Serial.print(steps);
    Serial.println(" steps.");
  
    if(direct == 1) {
        digitalWrite(m[dir_pin], HIGH);
    } else {
        digitalWrite(m[dir_pin], LOW);
    }
  
    for(int i=0; i < steps; i++) {
        motor_step(m);
    }
 
    digitalWrite(m[sync_pin], HIGH);
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
