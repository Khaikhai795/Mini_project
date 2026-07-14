String inputString = "";         
bool stringComplete = false;     

void setup() {
  Serial.begin(9600);
  inputString.reserve(200);
  
  // Khai báo chân LED xuất dữ liệu từ chân số 2 đến chân số 6
  for(int i = 2; i <= 6; i++){
    pinMode(i, OUTPUT);
    digitalWrite(i, LOW); // Ban đầu tắt hết
  }
}

void loop() {
  if (stringComplete) {
    inputString.trim(); // Xóa khoảng trắng và ký tự xuống dòng \n
    
    // --- BỔ SUNG: Tắt hết các LED trước khi xử lý lệnh mới ---
    for(int i = 2; i <= 6; i++){
      digitalWrite(i, LOW);
    }
    
    // Kiểm tra chuỗi nhận được từ Python và bật LED tương ứng
    if (inputString == "led1:on") {
      digitalWrite(2, HIGH);
      Serial.println("processed cmd:led1:on");
    } 
    else if (inputString == "led2:on") {
      digitalWrite(3, HIGH);
      Serial.println("processed cmd:led2:on");
    } 
    else if (inputString == "led3:on") {
      digitalWrite(4, HIGH);
      Serial.println("processed cmd:led3:on");
    } 
    else if (inputString == "led4:on") {
      digitalWrite(5, HIGH);
      Serial.println("processed cmd:led4:on");
    } 
    else if (inputString == "led5:on") {
      digitalWrite(6, HIGH);
      Serial.println("processed cmd:led5:on");
    }
    else if (inputString == "all:off") {
      // Đèn đã được tắt toàn bộ ở vòng lặp phía trên
      Serial.println("processed cmd:all:off");
    }
    
    // Reset lại chuỗi để chờ lệnh tiếp theo
    inputString = "";
    stringComplete = false;
  }
}

// Hàm tự động chạy khi có dữ liệu Serial truyền đến
void serialEvent() {
  while (Serial.available()) {
    char inChar = (char)Serial.read();
    inputString += inChar;
    if (inChar == '\n') {
      stringComplete = true;
    }
  }
}