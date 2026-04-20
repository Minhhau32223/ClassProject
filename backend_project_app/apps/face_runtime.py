from pathlib import Path

try:
    import cv2
    import numpy as np
    from scipy.spatial.distance import cosine
    from mtcnn import MTCNN
    from keras_facenet import FaceNet

    detector = MTCNN()
    embedder = FaceNet()
except ImportError as e:
    print(
        f"WARNING: Missing AI dependencies ({e}). "
        "Please run: pip install mtcnn keras-facenet opencv-python numpy scipy"
    )
    detector = None
    embedder = None
    cv2 = None
    np = None
    cosine = None


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = PROJECT_ROOT / "apps" / "ml"

FACE_DETECTION_MIN_CONFIDENCE = 0.85
FACE_MIN_SIZE_PX = 56
FACE_MIN_RELATIVE_SIZE = 0.10
DEFAULT_FACE_MATCH_THRESHOLD = 0.45
REGISTRATION_MAX_INTRA_DISTANCE = 0.35
DEFAULT_FACE_MATCH_MARGIN = 0.05
MIN_BRIGHTNESS_MEAN = 40
MAX_BRIGHTNESS_MEAN = 215
MIN_LAPLACIAN_VARIANCE = 12
ANTI_SPOOF_THRESHOLD = 0.40
ANTI_SPOOF_MODEL_PATH = MODEL_DIR / "anti_spoof_model.npz"
ANTI_SPOOF_MODEL_FALLBACK_PATH = PROJECT_ROOT / "reports" / "anti_spoof_training_full_v1" / "anti_spoof_model.npz"

anti_spoof_weights = None
anti_spoof_bias = None
anti_spoof_feature_mean = None
anti_spoof_feature_std = None


def load_anti_spoof_model():
    global anti_spoof_weights, anti_spoof_bias, anti_spoof_feature_mean, anti_spoof_feature_std

    if np is None:
        return

    model_path = ANTI_SPOOF_MODEL_PATH if ANTI_SPOOF_MODEL_PATH.exists() else ANTI_SPOOF_MODEL_FALLBACK_PATH
    if not model_path.exists():
        print(
            "WARNING: Anti-spoof model not found at "
            f"{ANTI_SPOOF_MODEL_PATH} or fallback {ANTI_SPOOF_MODEL_FALLBACK_PATH}"
        )
        return

    try:
        model_data = np.load(model_path)
        anti_spoof_weights = model_data["weights"].astype("float32")
        anti_spoof_bias = float(model_data["bias"][0])
        anti_spoof_feature_mean = model_data["feature_mean"].astype("float32")
        anti_spoof_feature_std = model_data["feature_std"].astype("float32")
    except Exception as exc:
        print(f"WARNING: Failed to load anti-spoof model ({exc})")
        anti_spoof_weights = None
        anti_spoof_bias = None
        anti_spoof_feature_mean = None
        anti_spoof_feature_std = None


def preprocess_face(img_rgb, box):
    x, y, w, h = box
    x1, y1 = max(0, x), max(0, y)
    x2 = min(img_rgb.shape[1], x + w)
    y2 = min(img_rgb.shape[0], y + h)

    face = img_rgb[y1:y2, x1:x2]
    if face.size == 0:
        return None

    return cv2.resize(face, (160, 160))


def estimate_pose_from_keypoints(keypoints):
    if not keypoints:
        return "unknown", 0.0

    left_eye = np.array(keypoints.get("left_eye", (0, 0)), dtype="float32")
    right_eye = np.array(keypoints.get("right_eye", (0, 0)), dtype="float32")
    nose = np.array(keypoints.get("nose", (0, 0)), dtype="float32")

    eye_distance = float(np.linalg.norm(right_eye - left_eye))
    if eye_distance <= 1e-6:
        return "unknown", 0.0

    eye_mid = (left_eye + right_eye) / 2.0
    yaw_score = float((nose[0] - eye_mid[0]) / eye_distance)

    if yaw_score <= -0.06:
        return "right", yaw_score
    if yaw_score >= 0.06:
        return "left", yaw_score
    return "front", yaw_score


def l2_normalize(x):
    norm = np.linalg.norm(x)
    if norm == 0:
        return x
    return x / norm


def sigmoid(x):
    x = np.clip(x, -40.0, 40.0)
    return 1.0 / (1.0 + np.exp(-x))


def _parse_vector(vector):
    import ast
    import json

    if isinstance(vector, list):
        return vector

    try:
        return json.loads(vector)
    except Exception:
        return ast.literal_eval(vector)


def cosine_distance_between(vector1, vector2):
    v1 = l2_normalize(np.array(_parse_vector(vector1)))
    v2 = l2_normalize(np.array(_parse_vector(vector2)))
    return float(cosine(v1, v2))


def extract_crop_statistics(face_rgb):
    gray = cv2.cvtColor(face_rgb.astype("uint8"), cv2.COLOR_RGB2GRAY)
    gray_float = gray.astype("float32") / 255.0

    gray_mean = float(np.mean(gray_float))
    gray_std = float(np.std(gray_float))
    rgb_mean = np.mean(face_rgb.astype("float32") / 255.0, axis=(0, 1))
    rgb_std = np.std(face_rgb.astype("float32") / 255.0, axis=(0, 1))

    lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    edges = cv2.Canny(gray, 80, 160)
    edge_density = float(np.mean(edges > 0))

    freq = np.fft.fftshift(np.fft.fft2(gray_float))
    magnitude = np.abs(freq)
    height, width = gray.shape
    yy, xx = np.ogrid[:height, :width]
    cy, cx = height / 2.0, width / 2.0
    radius = min(height, width) * 0.18
    mask = ((yy - cy) ** 2 + (xx - cx) ** 2) >= (radius ** 2)
    high_freq_ratio = float(np.sum(magnitude[mask]) / (np.sum(magnitude) + 1e-8))

    hist, _ = np.histogram(gray_float, bins=16, range=(0.0, 1.0), density=True)
    hist = hist.astype("float32")

    return np.concatenate(
        [
            rgb_mean.astype("float32"),
            rgb_std.astype("float32"),
            np.array([gray_mean, gray_std, lap_var, edge_density, high_freq_ratio], dtype="float32"),
            hist,
        ]
    )


def build_anti_spoof_feature_vector(embedding, diagnostics, face_rgb):
    scalar_features = np.array(
        [
            float(diagnostics.get("brightness_mean", 0.0)),
            float(diagnostics.get("laplacian_variance", 0.0)),
            float(diagnostics.get("face_confidence", 0.0)),
            float(diagnostics.get("relative_face_size", 0.0)),
            float(diagnostics.get("yaw_score", 0.0)),
        ],
        dtype="float32",
    )
    crop_features = extract_crop_statistics(face_rgb)
    return np.concatenate([np.array(embedding, dtype="float32"), scalar_features, crop_features]).astype("float32")


def predict_anti_spoof_score(feature_vector):
    if anti_spoof_weights is None or anti_spoof_feature_mean is None or anti_spoof_feature_std is None:
        return None, "unknown"

    normalized = (feature_vector - anti_spoof_feature_mean) / anti_spoof_feature_std
    score = float(sigmoid(np.dot(normalized, anti_spoof_weights) + anti_spoof_bias))
    label = "real" if score >= ANTI_SPOOF_THRESHOLD else "fake"
    return score, label


def get_embedding_from_image(image_bytes):
    embedding, _, _ = validate_face_image(image_bytes)
    return embedding


def validate_face_image(image_bytes):
    if detector is None or embedder is None:
        raise RuntimeError("AI Models not initialized")

    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Invalid image")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    brightness_mean = float(np.mean(gray))
    laplacian_variance = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    base_meta = {
        "brightness_mean": brightness_mean,
        "laplacian_variance": laplacian_variance,
    }

    if brightness_mean < MIN_BRIGHTNESS_MEAN:
        return None, "Ảnh quá tối. Vui lòng tăng ánh sáng trước khi chụp.", base_meta

    if brightness_mean > MAX_BRIGHTNESS_MEAN:
        return None, "Ảnh bị cháy sáng. Vui lòng tránh nguồn sáng quá mạnh hoặc đổi góc chụp.", base_meta

    if laplacian_variance < MIN_LAPLACIAN_VARIANCE:
        return None, "Ảnh bị mờ. Vui lòng giữ camera ổn định và chụp lại rõ hơn.", base_meta

    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = detector.detect_faces(img_rgb)
    if not results:
        return None, "Không phát hiện khuôn mặt trong ảnh. Vui lòng đưa mặt vào giữa khung hình.", base_meta

    results = [face for face in results if face["confidence"] >= FACE_DETECTION_MIN_CONFIDENCE]
    if not results:
        return None, "Khuôn mặt chưa rõ hoặc chưa đủ điều kiện nhận diện. Vui lòng chụp gần hơn và đủ sáng.", base_meta

    if len(results) > 1:
        results = sorted(results, key=lambda face: face["confidence"], reverse=True)

    best_face = max(results, key=lambda face: face["confidence"])
    x, y, w, h = best_face["box"]
    if w <= 0 or h <= 0:
        return None, "Không xác định được vùng khuôn mặt hợp lệ trong ảnh.", base_meta

    image_height, image_width = img_rgb.shape[:2]
    if w < FACE_MIN_SIZE_PX or h < FACE_MIN_SIZE_PX:
        return None, "Khuôn mặt quá nhỏ trong ảnh. Vui lòng tiến gần camera hơn.", base_meta

    if (w / image_width) < FACE_MIN_RELATIVE_SIZE or (h / image_height) < FACE_MIN_RELATIVE_SIZE:
        return None, "Khuôn mặt chiếm quá ít diện tích ảnh. Vui lòng đưa mặt vào gần hơn.", base_meta

    cropped_face = preprocess_face(img_rgb, best_face["box"])
    if cropped_face is None:
        return None, "Không cắt được khuôn mặt hợp lệ từ ảnh.", base_meta

    embed_input = np.expand_dims(cropped_face.astype("float32"), axis=0)
    embedding = embedder.embeddings(embed_input)[0]
    embedding = l2_normalize(embedding)
    pose_label, yaw_score = estimate_pose_from_keypoints(best_face.get("keypoints"))
    relative_face_size = max(float(w / image_width), float(h / image_height))

    diagnostics = {
        **base_meta,
        "face_confidence": float(best_face["confidence"]),
        "face_width": int(w),
        "face_height": int(h),
        "relative_face_size": relative_face_size,
        "pose_label": pose_label,
        "yaw_score": yaw_score,
    }

    anti_spoof_features = build_anti_spoof_feature_vector(embedding, diagnostics, cropped_face)
    anti_spoof_score, anti_spoof_label = predict_anti_spoof_score(anti_spoof_features)
    diagnostics["anti_spoof_score"] = anti_spoof_score
    diagnostics["anti_spoof_label"] = anti_spoof_label
    diagnostics["anti_spoof_threshold"] = ANTI_SPOOF_THRESHOLD

    if anti_spoof_label == "fake":
        return None, "Phát hiện ảnh giả hoặc không phải khuôn mặt thật trực tiếp trước camera.", diagnostics

    return embedding.tolist(), None, diagnostics


def compare_faces(vector1, vector2, threshold=DEFAULT_FACE_MATCH_THRESHOLD):
    distance = cosine_distance_between(vector1, vector2)
    return distance < threshold, distance


def get_average_embedding(vector_list):
    if not vector_list:
        return None

    arr = [l2_normalize(np.array(vector)) for vector in vector_list]
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


load_anti_spoof_model()
