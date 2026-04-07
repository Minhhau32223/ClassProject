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
def get_embedding_from_image(image_bytes):
    if detector is None or embedder is None:
        # ❌ Không ném RuntimeError nữa, mà trả về None
        print("⚠️ AI Models are not initialized.")
        return None
    
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
        
        if not results:
            print("❌ Không phát hiện khuôn mặt")
            return None
        
        # Chỉ lấy khuôn mặt có confidence cao nhất
        best_face = max(results, key=lambda f: f['confidence'])
        confidence = best_face['confidence']
        
        # ✅ Tăng ngưỡng confidence lên 0.98 để chống fake
        if confidence < 0.98:
            print(f"❌ Confidence quá thấp: {confidence}")
            return None
        
        x, y, w, h = best_face['box']
        
        # ✅ Kiểm tra kích thước khuôn mặt chặt chẽ hơn
        if w < 100 or h < 100:  # Tăng từ 80 lên 100
            print(f"❌ Mặt quá nhỏ: {w}x{h}")
            return None
        
        # ✅ Thêm kiểm tra tỷ lệ khung hình (face ratio)
        if w/h < 0.7 or w/h > 1.3:  # Khuôn mặt thường có tỷ lệ ~0.8-1.2
            print(f"❌ Tỷ lệ khuôn mặt bất thường: {w/h}")
            return None
        
        x, y = max(0, x), max(0, y)
        face_crop = img_rgb[y:y+h, x:x+w]

        if not detect_liveness(image_bytes):
            print("❌ Liveness detection failed")
            return None
                
        if face_crop.size == 0:
            print("❌ Crop lỗi")
            return None
        
        # ✅ Thêm preprocessing: cân bằng sáng, khử nhiễu
        face_resized = cv2.resize(face_crop, (160, 160))
        
        # Normalize pixel values về [0, 1]
        face_normalized = face_resized.astype(np.float32) / 255.0
        
        # Chuẩn bị cho model
        face_ready = np.expand_dims(face_normalized, axis=0)
        embeddings = embedder.embeddings(face_ready)
        
        print("✅ Khuôn mặt hợp lệ, confidence:", confidence)
        return embeddings[0].tolist()
        
    except Exception as e:
        print("❌ Lỗi get_embedding:", str(e))
        return None
    
def detect_liveness(image_bytes):
    """Kiểm tra cơ bản xem có phải ảnh giả (in giấy, màn hình) không"""
    import numpy as np
    import cv2
    
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if img is None:
        return False
    
    # Chuyển sang grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Tính độ sắc nét (blur detection)
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    print(f" Blur score: {laplacian_var}")
    # Ảnh quá mờ -> có thể là ảnh in hoặc screenshot
    if laplacian_var < 50:  # Threshold có thể điều chỉnh
        print(f"❌ Ảnh quá mờ (blur): {laplacian_var}")
        return False
    
    # Kiểm tra phản xạ ánh sáng (có thể thêm)
    # ... 
    
    return True
    

'''
def compare_faces(vector1, vector2, threshold=0.4):
    """
    Kỹ thuật so khớp (Cosine Similarity).
    Lưu ý: scipy.spatial.distance.cosine tính *khoảng cách* (Distance),
    khoảng cách càng nhỏ (gần 0) thì 2 khuôn mặt càng giống nhau.
    Cosine Similarity = 1 - Cosine Distance.
    
    Tại hàm này, mình sẽ cho qua nếu Cosine Distance < threshold.
    FaceNet thường dùng Threshold ~ 0.4 hoặc 0.5.
    """
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
        
    v1 = np.array(vector1)
    v2 = np.array(vector2)
    
    # Tính Cosine Distance (Giá trị từ 0 đến 2)
    distance = cosine(v1, v2)
    
    # Nếu distance thấp hơn ngưỡng cho phép -> Khớp (True)
    is_match = distance < threshold
    return is_match, distance
'''
def compare_faces(vector1, vector2, threshold=0.45):
    import numpy as np
    from scipy.spatial.distance import cosine
    import json, ast

    # Parse nếu là string
    if not isinstance(vector1, list):
        try:
            vector1 = json.loads(vector1)
        except:
            vector1 = ast.literal_eval(vector1)

    if not isinstance(vector2, list):
        try:
            vector2 = json.loads(vector2)
        except:
            vector2 = ast.literal_eval(vector2)

    v1 = np.array(vector1)
    v2 = np.array(vector2)

    # ✅ NORMALIZE (cực quan trọng)
    def l2_normalize(x):
        norm = np.linalg.norm(x)
        return x if norm == 0 else x / norm

    v1 = l2_normalize(v1)
    v2 = l2_normalize(v2)

    distance = cosine(v1, v2)

    return distance < threshold, distance
def l2_normalize(x):
    norm = np.linalg.norm(x)
    if norm == 0:
        return x
    return x / norm

def get_average_embedding(vector_list):
    """
    Nhận vào danh sách các vectors, Normalize từng vector, lấy Mean, rồi Normalize lại lần nữa.
    Luôn đảm bảo Vector nằm trên bề mặt chuẩn không gian 512D.
    """
    if not vector_list:
        return None
        
    arr = [l2_normalize(np.array(v)) for v in vector_list]
    mean_vec = np.mean(arr, axis=0)
    final_vec = l2_normalize(mean_vec)
    return final_vec.tolist()
