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

def get_embedding_from_image(image_bytes):
    """
    Nhận mảng byte của hình ảnh, dùng MTCNN để phát hiện khuôn mặt,
    rồi dùng FaceNet để trích xuất vector đặc trưng (Embedding 512D).
    Trả về mảng float (vector) hoặc None nếu không tìm thấy khuôn mặt.
    """
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

    # Lấy khuôn mặt có độ tự tin (confidence) cao nhất hoặc lớn nhất
    # Trong phiên bản đơn giản, lấy khuôn mặt đầu tiên tìm được
    bounding_box = results[0]['box']
    x, y, w, h = bounding_box
    
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

def compare_faces(vector1, vector2, threshold=0.4):
    """
    Kỹ thuật so khớp (Cosine Similarity).
    Lưu ý: scipy.spatial.distance.cosine tính *khoảng cách* (Distance),
    khoảng cách càng nhỏ (gần 0) thì 2 khuôn mặt càng giống nhau.
    Cosine Similarity = 1 - Cosine Distance.
    
    Tại hàm này, mình sẽ cho qua nếu Cosine Distance < threshold.
    FaceNet thường dùng Threshold ~ 0.4 hoặc 0.5.
    """
    if not isinstance(vector1, list):
        vector1 = eval(vector1)
    if not isinstance(vector2, list):
        vector2 = eval(vector2)
        
    v1 = np.array(vector1)
    v2 = np.array(vector2)
    
    # Tính Cosine Distance (Giá trị từ 0 đến 2)
    distance = cosine(v1, v2)
    
    # Nếu distance thấp hơn ngưỡng cho phép -> Khớp (True)
    is_match = distance < threshold
    return is_match, distance
