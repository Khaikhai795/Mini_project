import cv2
import mediapipe as mp
import serial
import time
import os

# --- KẾT NỐI SERIAL ---
try:
    ser = serial.Serial('COM2', 9600, timeout=1)
    print("Đã kết nối thành công tới cổng COM2!")
    time.sleep(2) 
except Exception as e:
    print(f"Không thể kết nối cổng COM: {e}")
    ser = None

# --- CẤU HÌNH MEDIAPIPE ---
BaseOptions = mp.tasks.BaseOptions
HandLandmarker = mp.tasks.vision.HandLandmarker
HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
VisionRunningMode = mp.tasks.vision.RunningMode

model_path = 'hand_landmarker.task'
options = HandLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=model_path),
    running_mode=VisionRunningMode.VIDEO,
    num_hands=1
)

# --- BIẾN PHỤC VỤ LỌC NHIỄU (STABILIZATION) ---
last_sent_fingers = -1  # Trạng thái cuối cùng đã gửi xuống Arduino
current_candidate = -1  # Số ngón tay đang nghi ngờ là đúng
candidate_count = 0     # Số lần số ngón tay này xuất hiện liên tiếp
STABILITY_THRESHOLD = 6  # Cần ổn định liên tiếp 6 khung hình mới đổi lệnh (khoảng 0.2 giây)

cap = cv2.VideoCapture(0)

with HandLandmarker.create_from_options(options) as landmarker:
    while cap.isOpened():
        success, img = cap.read()
        if not success:
            break
        
        img = cv2.flip(img, 1)
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_rgb)
        timestamp_ms = int(time.time() * 1000)
        detection_result = landmarker.detect_for_video(mp_image, timestamp_ms)
        
        detected_fingers = 0
        
        if detection_result.hand_landmarks:
            landmarks = detection_result.hand_landmarks[0]
            fingers = []
            
            # Ngón cái
            if landmarks[4].x < landmarks[3].x:
                fingers.append(1)
            else:
                fingers.append(0)
                
            # 4 ngón còn lại
            for tip_id in [8, 12, 16, 20]:
                if landmarks[tip_id].y < landmarks[tip_id - 2].y:
                    fingers.append(1)
                else:
                    fingers.append(0)
            
            detected_fingers = fingers.count(1)
            
            # Vẽ các khớp tay
            for lm in landmarks:
                h, w, c = img.shape
                cx, cy = int(lm.x * w), int(lm.y * h)
                cv2.circle(img, (cx, cy), 5, (0, 255, 0), cv2.FILLED)
        
        # --- THUẬT TOÁN LỌC NHIỄU CHỐNG NHÁY ---
        if detected_fingers == current_candidate:
            candidate_count += 1
        else:
            current_candidate = detected_fingers
            candidate_count = 1
            
        # Nếu số ngón tay duy trì ổn định đủ số khung hình quy định
        if candidate_count >= STABILITY_THRESHOLD:
            if current_candidate != last_sent_fingers:
                last_sent_fingers = current_candidate
                
                # Gửi lệnh xuống Arduino
                if ser and ser.is_open:
                    if last_sent_fingers == 1:
                        ser.write(b"led1:on\n")
                    elif last_sent_fingers == 2:
                        ser.write(b"led2:on\n")
                    elif last_sent_fingers == 3:
                        ser.write(b"led3:on\n")
                    elif last_sent_fingers == 4:
                        ser.write(b"led4:on\n")
                    elif last_sent_fingers == 5:
                        ser.write(b"led5:on\n")
                    else:
                        ser.write(b"all:off\n")
                    print(f"--> ĐÃ GỬI LỆNH THAY ĐỔI: {last_sent_fingers} ngón")

        # Hiển thị thông tin lên màn hình camera
        cv2.putText(img, f"Detecting: {detected_fingers}", (45, 60), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        cv2.putText(img, f"Stable State: {last_sent_fingers}", (45, 120), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)
        
        cv2.imshow("Hand Tracking", img)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
if ser:
    ser.close()
cv2.destroyAllWindows()