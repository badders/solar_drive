int clock = 1;
int dir = 0;
int sync = 2;

int m1pins[] = {46, 47, 48, 49};
int m2pins[] = {42, 43, 44, 45};

void setup() {
    Serial.begin(9600);
   for(int i=0; i<4; i++){
     pinMode(m1pins[i], OUTPUT);
     pinMode(m2pins[i], OUTPUT);
   }
   digitalWrite(m1pins[sync], HIGH);
   digitalWrite(m2pins[sync], HIGH);
   digitalWrite(m2pins[dir], LOW);
   digitalWrite(m1pins[dir], LOW);
   Serial.println("Listening for status changes ...");
}

void motor_step(int *m) {
  digitalWrite(m[clock], HIGH);
  delayMicroseconds(50);
  digitalWrite(m[clock], LOW);
  delayMicroseconds(50);
}

void turn(int motor, int direct, int steps) {
  int *m;
  
  if(motor == 1) {
    m = m1pins;
  }
  else {
    m = m2pins;
  }
  
  digitalWrite(m[sync], LOW);
  
  Serial.print("Turning Motor ");
  Serial.print(motor);
  Serial.print(" for ");
  Serial.print(steps);
  Serial.println(" steps.");
  
  if(direct == 1) {
    digitalWrite(m[dir], HIGH);
  }
  else {
    digitalWrite(m[dir], LOW);
  }
  
  for(int i=0; i < steps; i++) {
    motor_step(m);
  }
 
  digitalWrite(m[sync], HIGH);
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
