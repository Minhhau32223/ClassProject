# import os
# # --- Import các thư viện chính ---
# try:
#     import cv2
#     import numpy as np
#     from scipy.spatial.distance import cosine
#     from mtcnn import MTCNN
#     from keras_facenet import FaceNet
#     from deepface_antispoofing import DeepFaceAntiSpoofing # Import thư viện chống giả

#     print("Đang tải các mô hình AI. Vui lòng đợi...")

#     # 1. Khởi tạo bộ phát hiện khuôn mặt (MTCNN)
#     detector = MTCNN()

#     # 2. Khởi tạo bộ trích xuất đặc trưng (FaceNet)
#     embedder = FaceNet()

#     # 3. Khởi tạo bộ phát hiện ảnh giả / vật thể (Anti-spoofing)
#     spoof_detector = DeepFaceAntiSpoofing()

#     print("Tất cả các mô hình đã sẵn sàng.")

# except ImportError as e:
#     print(f"LỖI: Thiếu thư viện ({e}). Vui lòng chạy lệnh:")
#     print("pip install mtcnn keras-facenet opencv-python numpy scipy deepface-antispoofing")
#     # Gán tất cả là None để chương trình không bị crash nếu thiếu thư viện
#     detector = None
#     embedder = None
#     spoof_detector = None
#     cv2 = None
#     np = None
#     cosine = None

# # --- HÀM CHÍNH ĐÃ ĐƯỢC TÍCH HỢP CHỐNG GIẢ ---
# def get_embedding_from_image(image_bytes):
#     """
#     Nhận mảng byte của hình ảnh.
#     B1: Kiểm tra ảnh giả/vật thể (Anti-spoofing).
#     B2: Dùng MTCNN để phát hiện khuôn mặt.
#     B3: Dùng FaceNet để trích xuất vector đặc trưng (Embedding 512D).
#     Trả về vector (list) hoặc None nếu là ảnh giả hoặc không tìm thấy khuôn mặt.
    
#     # Kiểm tra các model đã được khởi tạo thành công chưa
#     if detector is None or embedder is None or spoof_detector is None:
#         raise RuntimeError("Các mô hình AI chưa được khởi tạo. Hãy kiểm tra lại việc cài đặt thư viện.")

#     # --- BƯỚC 0: CHỐNG GIẢ MẠO & VẬT THỂ (XỬ LÝ CHAI NƯỚC) ---
#     # Lưu ảnh tạm thời từ byte array để thư viện deepface-antispoofing có thể đọc
#     """
#     temp_image_path = "temp_check.jpg"
#     try:
#         with open(temp_image_path, "wb") as f:
#             f.write(image_bytes)

#         # Gọi hàm phân tích của deepface-antispoofing
#         # Hàm này trả về dictionary với key 'is_real' (string: 'True' hoặc 'False')
#         result = spoof_detector.analyze_deepface(temp_image_path)
#         is_live = result.get('is_real') == 'True'
#         spoof_type = result.get('spoof_type', 'Không xác định')

#         if not is_live:
#             print(f"CẢNH BÁO: Từ chối điểm danh. Phát hiện vật thể/ảnh giả: {spoof_type}")
#             return None  # Dừng lại ngay, không cho điểm danh
#         else:
#             print("Xác thực: Đây là người thật. Tiến hành nhận diện...")
#             # Xóa file tạm sau khi kiểm tra xong
#             if os.path.exists(temp_image_path):
#                 os.remove(temp_image_path)
#     except Exception as e:
#         print(f"Lỗi khi kiểm tra chống giả mạo: {e}")
#         # Tùy chọn: Có thể vẫn cho phép xử lý tiếp hoặc trả về None
#         # Ở đây mình chọn dừng lại để đảm bảo an toàn
#         return None
    
#     # --- BƯỚC 1: ĐỌC VÀ PHÁT HIỆN KHUÔN MẶT (MTCNN) ---
#     nparr = np.frombuffer(image_bytes, np.uint8)
#     img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

#     if img is None:
#         raise ValueError("Không thể đọc được hình ảnh tải lên.")

#     # MTCNN yêu cầu ảnh ở định dạng RGB
#     img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

#     # Phát hiện tất cả các khuôn mặt trong ảnh
#     results = detector.detect_faces(img_rgb)

#     if not results:
#         print("CẢNH BÁO: Không tìm thấy khuôn mặt nào trong ảnh.")
#         return None

#     # Chọn khuôn mặt có độ tin cậy cao nhất
#     best_face = max(results, key=lambda f: f['confidence'])
#     bounding_box = best_face['box']
#     x, y, w, h = bounding_box

#     if w <= 0 or h <= 0:
#         print(" CẢNH BÁO: Kích thước khuôn mặt không hợp lệ.")
#         return None

#     # Cắt và xử lý khuôn mặt
#     x_start, y_start = max(0, x), max(0, y)
#     face_crop = img_rgb[y_start:y_start+h, x_start:x_start+w]
#     face_resized = cv2.resize(face_crop, (160, 160))  # FaceNet yêu cầu kích thước 160x160
#     face_ready = np.expand_dims(face_resized, axis=0)

#     # --- BƯỚC 2: TRÍCH XUẤT VECTOR ĐẶC TRƯNG (FaceNet) ---
#     embeddings = embedder.embeddings(face_ready)

#     # Trả về vector dưới dạng list
#     return embeddings[0].tolist()

# # --- CÁC HÀM SO SÁNH VECTOR VÀ CÁC HÀM TIỆN ÍCH KHÁC ---
# # (Phần này bạn giữ nguyên như code cũ)

# def compare_faces(vector1, vector2, threshold=0.4):
#     """
#     So sánh hai vector bằng khoảng cách Cosine.
#     Trả về: (is_match, distance)
#     """
#     # (Nội dung hàm này bạn giữ nguyên)
#     import json
#     import ast
#     # ... (code giữ nguyên) ...
#     # Xử lý chuyển đổi kiểu dữ liệu
#     if not isinstance(vector1, list):
#         try:
#             vector1 = json.loads(vector1)
#         except Exception:
#             vector1 = ast.literal_eval(vector1)
#     if not isinstance(vector2, list):
#         try:
#             vector2 = json.loads(vector2)
#         except Exception:
#             vector2 = ast.literal_eval(vector2)

#     v1 = np.array(vector1)
#     v2 = np.array(vector2)

#     # Tính Cosine Distance (Giá trị từ 0 đến 2)
#     # Lưu ý: distance càng nhỏ (gần 0) thì 2 khuôn mặt càng giống nhau
#     distance = cosine(v1, v2)

#     # Nếu distance thấp hơn ngưỡng cho phép -> Khớp (True)
#     is_match = distance < threshold
#     return is_match, distance

# def l2_normalize(x):
#     """Chuẩn hóa vector về độ dài đơn vị (Unit vector)"""
#     norm = np.linalg.norm(x)
#     if norm == 0:
#         return x
#     return x / norm

# def get_average_embedding(vector_list):
#     """
#     Tính vector trung bình từ danh sách các vector.
#     Phương pháp: Normalize từng vector -> Lấy trung bình -> Normalize kết quả.
#     """
#     if not vector_list:
#         return None

#     arr = [l2_normalize(np.array(v)) for v in vector_list]
#     mean_vec = np.mean(arr, axis=0)
#     final_vec = l2_normalize(mean_vec)
#     return final_vec.tolist()




import os


# Cố gắng import mtcnn, keras_facenet, cv2, numpy, scipy
try:
    import cv2
    import numpy as np
    from scipy.spatial.distance import cosine
    from mtcnn import MTCNN
    from keras_facenet import FaceNet
    
    # Khởi tạo mô hình (Tạo Singleton để tránh load lại model liên tục gây chậm API)
    detector = MTCNN()
    embedder = FaceNet()
except ImportError as e:
    print(f"WARNING: Missing AI dependencies ({e}). Please run: pip install mtcnn keras-facenet opencv-python numpy scipy")
    detector = None
    embedder = None
    cv2 = None
    np = None
    cosine = None

FACE_DETECTION_MIN_CONFIDENCE = 0.95
FACE_MIN_SIZE_PX = 90
FACE_MIN_RELATIVE_SIZE = 0.18
DEFAULT_FACE_MATCH_THRESHOLD = 0.32
REGISTRATION_MAX_INTRA_DISTANCE = 0.35
    """
def get_embedding_from_image(image_bytes):
    
    Nhận mảng byte của hình ảnh, dùng MTCNN để phát hiện khuôn mặt,
    rồi dùng FaceNet để trích xuất vector đặc trưng (Embedding 512D).
    Trả về mảng float (vector) hoặc None nếu không tìm thấy khuôn mặt.
    
    if detector is None or embedder is None:
        raise RuntimeError("AI Models are not initialized. Please install mtcnn and keras-facenet.")

    # 1. Decode ảnh từ mảng bytes sang ma trận OpenCV (màu BGR mặc định)
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        raise ValueError("Không thể đọc được hình ảnh tải lên.")

    # 2. MTCNN yêu cầu ảnh ở định dạng RGB
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    # Khúc 1: Phát hiện khuôn mặt (Face Detection)
    results = detector.detect_faces(img_rgb)
    
    if not results:
        # Không tìm thấy khuôn mặt nào
        return None

    # Lấy khuôn mặt có độ tự tin cao nhất thay vì phần tử đầu tiên (Fix Multi-Face)
    best_face = max(results, key=lambda f: f['confidence'])
    bounding_box = best_face['box']
    x, y, w, h = bounding_box
    
    # Validate cấu trúc hộp khuôn mặt lỗi
    if w <= 0 or h <= 0:
        return None
    
    # Cắt khuôn mặt khỏi ảnh gốc
    # Xử lý trường hợp bounding_box có tọa độ âm ở viền ảnh
    x_start, y_start = max(0, x), max(0, y)
    face_crop = img_rgb[y_start:y_start+h, x_start:x_start+w]
    
    # Cân chỉnh kích thước chuẩn cho FaceNet (thường là 160x160)
    face_resized = cv2.resize(face_crop, (160, 160))
    face_ready = np.expand_dims(face_resized, axis=0)
    
    # Khúc 2: Trích xuất đặc trưng (Feature Extraction) qua FaceNet
    embeddings = embedder.embeddings(face_ready)
    
    return embeddings[0].tolist() # Chuyển từ numpy array sang list
    """
'''
def get_embedding_from_image(image_bytes):
    if detector is None or embedder is None:
        raise RuntimeError("AI Models are not initialized.")

    try:
        import numpy as np
        import cv2

        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            print("❌ Không đọc được ảnh")
            return None

        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        results = detector.detect_faces(img_rgb)

        # ❌ Không phải khuôn mặt
        if not results:
            print("❌ Không phát hiện khuôn mặt")
            return None

        best_face = max(results, key=lambda f: f['confidence'])
        confidence = best_face['confidence']

        # ❌ Chặn fake (chai nước, vật thể)
        if confidence < 0.95:
            print("❌ Confidence thấp:", confidence)
            return None

        x, y, w, h = best_face['box']

        # ❌ Bounding box lỗi
        if w <= 0 or h <= 0:
            print("❌ Bounding box lỗi")
            return None

        # ❌ Mặt quá nhỏ (fake)
        if w < 80 or h < 80:
            print("❌ Mặt quá nhỏ:", w, h)
            return None

        x, y = max(0, x), max(0, y)
        face_crop = img_rgb[y:y+h, x:x+w]

        if face_crop.size == 0:
            print("❌ Crop lỗi")
            return None

        face_resized = cv2.resize(face_crop, (160, 160))
        face_ready = np.expand_dims(face_resized, axis=0)

        embeddings = embedder.embeddings(face_ready)

        print("✅ Khuôn mặt hợp lệ")

        return embeddings[0].tolist()

    except Exception as e:
        print("❌ Lỗi get_embedding:", str(e))
        return None
# def compare_faces(vector1, vector2, threshold=0.4):
#     import numpy as np
#     import json, ast
#     from scipy.spatial.distance import cosine

#     try:
#         if vector1 is None or vector2 is None:
#             print("❌ Vector None")
#             return False, 999

#         if not isinstance(vector1, list):
#             try:
#                 vector1 = json.loads(vector1)
#             except:
#                 vector1 = ast.literal_eval(vector1)

#         if not isinstance(vector2, list):
#             try:
#                 vector2 = json.loads(vector2)
#             except:
#                 vector2 = ast.literal_eval(vector2)

#         v1 = np.array(vector1)
#         v2 = np.array(vector2)

#         if v1.shape != v2.shape:
#             print("❌ Shape mismatch:", v1.shape, v2.shape)
#             return False, 999

#         distance = cosine(v1, v2)

#         print("📏 Distance:", distance)

#         return distance < threshold, distance

#     except Exception as e:
#         print("❌ Lỗi compare:", str(e))
#         return False, 999
    
'''
def preprocess_face(img_rgb, box):
    x, y, w, h = box

    x1, y1 = max(0, x), max(0, y)
    x2 = min(img_rgb.shape[1], x + w)
    y2 = min(img_rgb.shape[0], y + h)

    face = img_rgb[y1:y2, x1:x2]

    if face.size == 0:
        return None

    face = cv2.resize(face, (160, 160))

    # Normalize pixel về [-1, 1]
    face = face.astype("float32")
    face = (face - 127.5) / 128.0

    return face

def l2_normalize(x):
    norm = np.linalg.norm(x)
    if norm == 0:
        return x
    return x / norm


def cosine_distance_between(vector1, vector2):
    import json
    import ast

    if not isinstance(vector1, list):
        try:
            vector1 = json.loads(vector1)
        except Exception:
            vector1 = ast.literal_eval(vector1)

    if not isinstance(vector2, list):
        try:
            vector2 = json.loads(vector2)
        except Exception:
            vector2 = ast.literal_eval(vector2)

    v1 = l2_normalize(np.array(vector1))
    v2 = l2_normalize(np.array(vector2))
    return float(cosine(v1, v2))

def get_embedding_from_image(image_bytes):
    if detector is None or embedder is None:
        raise RuntimeError("AI Models not initialized")

    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        raise ValueError("Invalid image")

    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    results = detector.detect_faces(img_rgb)

    if not results:
        return None

    # Siết lại điều kiện phát hiện để giảm nhận nhầm
    results = [f for f in results if f['confidence'] >= FACE_DETECTION_MIN_CONFIDENCE]
    if not results:
        return None

    best_face = max(results, key=lambda f: f['confidence'])
    x, y, w, h = best_face['box']

    if w <= 0 or h <= 0:
        return None

    image_height, image_width = img_rgb.shape[:2]
    if w < FACE_MIN_SIZE_PX or h < FACE_MIN_SIZE_PX:
        return None

    if (w / image_width) < FACE_MIN_RELATIVE_SIZE or (h / image_height) < FACE_MIN_RELATIVE_SIZE:
        return None

    face = preprocess_face(img_rgb, best_face['box'])
    if face is None:
        return None

    face = np.expand_dims(face, axis=0)

    embedding = embedder.embeddings(face)[0]

    # normalize luôn tại đây
    embedding = l2_normalize(embedding)

    return embedding.tolist()

def compare_faces(vector1, vector2, threshold=DEFAULT_FACE_MATCH_THRESHOLD):
    distance = cosine_distance_between(vector1, vector2)
    is_match = distance < threshold
    return is_match, distance

def get_average_embedding(vector_list):
    if not vector_list:
        return None

    arr = [l2_normalize(np.array(v)) for v in vector_list]

    mean_vec = np.mean(arr, axis=0)

    return l2_normalize(mean_vec).tolist()


def registration_embeddings_are_consistent(embeddings, max_distance=REGISTRATION_MAX_INTRA_DISTANCE):
    if len(embeddings) < 2:
        return True, 0.0

    distances = []
    for i in range(len(embeddings)):
        for j in range(i + 1, len(embeddings)):
            distances.append(cosine_distance_between(embeddings[i], embeddings[j]))

    worst_distance = max(distances) if distances else 0.0
    return worst_distance <= max_distance, worst_distance
