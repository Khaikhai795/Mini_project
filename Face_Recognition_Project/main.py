import cv2
import face_recognition
import os
import numpy as np
from PIL import Image

# --- CẤU HÌNH HỆ THỐNG ---
MOTION_THRESHOLD = 3.0       # Ngưỡng dịch chuyển tối thiểu (nhẹ nhàng)
REQUIRED_MOVEMENT_FRAMES = 6  # Số khung hình cần chuyển động để đạt 100%
HOLD_IDENTITY_FRAMES = 15     # Giữ nguyên danh tính trong 15 khung hình tránh mất dấu khi nghiêng mặt
STRICT_TOLERANCE = 0.38       # THẮT CHẶT SAI SỐ (Hạn chế tối đa nhận diện nhầm người khác)

# Các biến trạng thái toàn cục
prev_face_center = None
movement_score = 0
is_verified = False

locked_name = "Unknown"       # KHÓA DANH TÍNH: Chỉ xác thực duy nhất người này trong 1 phiên
identity_hold_counter = 0     # Bộ đệm giữ danh tính

# --- 1. NẠP DỮ LIỆU KHUÔN MẶT MẪU ---
known_face_encodings = []
known_face_names = []
image_folder = "images"

print("Đang nạp dữ liệu khuôn mặt mẫu...")
if not os.path.exists(image_folder):
    os.makedirs(image_folder)

for file_name in os.listdir(image_folder):
    if file_name.lower().endswith((".jpg", ".png", ".jpeg")):
        name = os.path.splitext(file_name)[0].replace("_", " ").title()
        image_path = os.path.join(image_folder, file_name)
        try:
            with Image.open(image_path) as pil_img:
                canvas = Image.new("RGB", pil_img.size, (255, 255, 255))
                canvas.paste(pil_img, mask=pil_img.split()[-1] if pil_img.mode == 'RGBA' else None)
                image = np.array(canvas)
            encodings = face_recognition.face_encodings(image)
            if len(encodings) > 0:
                known_face_encodings.append(encodings[0])
                known_face_names.append(name)
                print(f"-> Đã nạp khuôn mặt: {name}")
        except Exception as e:
            print(f"❌ Lỗi ảnh {file_name}: {e}")

if not known_face_encodings:
    print("❌ LỖI: Thư mục 'images' trống.")
    exit()

print("Khởi động Camera chống nhảy danh tính...")
cap = cv2.VideoCapture(1) # Đổi thành 0 nếu dùng webcam laptop thường

process_this_frame = True

while cap.isOpened():
    success, frame = cap.read()
    if not success: 
        print("Không thể kết nối camera.")
        break
        
    frame = cv2.flip(frame, 1)
    
    # Chia đôi ảnh để CPU xử lý mượt mà
    small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
    rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

    if process_this_frame:
        face_locations = face_recognition.face_locations(rgb_small_frame)
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

    process_this_frame = not process_this_frame

    current_detected_name = "Unknown"
    current_location = None

    # 1. NHẬN DIỆN DANH TÍNH KHUNG HÌNH HIỆN TẠI
    if len(face_locations) > 0:
        current_location = face_locations[0]
        if len(face_encodings) > 0:
            face_encoding = face_encodings[0]
            # Áp dụng ngưỡng nghiêm ngặt STRICT_TOLERANCE để tránh nhận diện sai
            matches = face_recognition.compare_faces(known_face_encodings, face_encoding, tolerance=STRICT_TOLERANCE)
            face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
            if len(face_distances) > 0:
                best_match_index = np.argmin(face_distances)
                if matches[best_match_index]:
                    current_detected_name = known_face_names[best_match_index]

    # --- 2. LOGIC KHÓA DANH TÍNH CHỐNG NHẢY TÊN ---
    if current_detected_name != "Unknown":
        if locked_name == "Unknown":
            # Nếu chưa khóa ai -> Tiến hành khóa danh tính người vừa xuất hiện
            locked_name = current_detected_name
            print(f"🔒 Đã khóa danh tính cần xác thực: {locked_name}")
        
        # Nếu người đang nhận diện trùng với người đang bị khóa -> Làm mới bộ đệm thời gian
        if current_detected_name == locked_name:
            identity_hold_counter = HOLD_IDENTITY_FRAMES
            
    else:
        # Nếu tạm thời mất dấu (Unknown) -> Giảm dần thời gian giữ danh tính
        if identity_hold_counter > 0:
            identity_hold_counter -= 1
        else:
            # Hết thời gian giữ -> Giải phóng khóa để cho phép nhận diện người mới
            if locked_name != "Unknown":
                print(f"🔓 Đã mở khóa danh tính (Hết thời gian chờ)")
            locked_name = "Unknown"
            prev_face_center = None
            movement_score = 0
            is_verified = False

    # --- 3. ĐO CHUYỂN ĐỘNG (CHỈ ÁP DỤNG CHO NGƯỜI ĐANG BỊ KHÓA) ---
    if locked_name != "Unknown" and current_location is not None:
        top, right, bottom, left = current_location
        top *= 2; right *= 2; bottom *= 2; left *= 2

        center_x = (left + right) / 2
        center_y = (top + bottom) / 2
        current_center = np.array([center_x, center_y])

        if prev_face_center is not None and not is_verified:
            distance = np.linalg.norm(current_center - prev_face_center)
            
            # Ghi nhận chuyển động gật/lắc đầu
            if distance > MOTION_THRESHOLD:
                movement_score = min(REQUIRED_MOVEMENT_FRAMES, movement_score + 1.5) # Cộng điểm nhanh
            else:
                movement_score = max(0, movement_score - 0.1)

            if movement_score >= REQUIRED_MOVEMENT_FRAMES:
                is_verified = True
        
        prev_face_center = current_center

    # --- 4. HIỂN THỊ GIAO DIỆN CHUẨN XÁC ---
    if len(face_locations) > 0 and current_location is not None:
        top, right, bottom, left = current_location
        top *= 2; right *= 2; bottom *= 2; left *= 2

        # Giao diện hiển thị dựa trên danh tính ĐANG BỊ KHÓA (locked_name)
        if locked_name == "Unknown":
            color = (0, 0, 255) # Đỏ
            status_text = "UNKNOWN FACE"
            action_text = "Access Denied"
        elif is_verified:
            color = (0, 255, 0) # Xanh lá
            status_text = f"{locked_name} (VERIFIED)"
            action_text = "Verification Successful!"
        else:
            color = (0, 165, 255) # Cam
            status_text = f"{locked_name} (PENDING)"
            progress = int((movement_score / REQUIRED_MOVEMENT_FRAMES) * 100)
            progress = min(100, max(0, progress))
            action_text = f"Nod or move head... {progress}%"

        cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
        cv2.rectangle(frame, (left, bottom - 60), (right, bottom), color, cv2.FILLED)
        cv2.putText(frame, status_text, (left + 6, bottom - 35), cv2.FONT_HERSHEY_DUPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(frame, action_text, (left + 6, bottom - 10), cv2.FONT_HERSHEY_DUPLEX, 0.45, (255, 255, 255), 1)

    cv2.imshow("He thong Nhan dien - Locked Identity", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()