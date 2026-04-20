import argparse
import csv
import json
import math
import random
import sys
import time
import shutil
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apps import face_runtime as face_utils
from apps.face_runtime import validate_face_image


MODEL_EXPORT_PATH = PROJECT_ROOT / "apps" / "ml" / "anti_spoof_model.npz"


VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
TARGET_ACCURACY = 0.85
TARGET_FAR = 0.20
TARGET_FRR = 0.10


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Train anti-spoof model rieng cho bai toan REAL / FAKE. "
            "FaceNet khong duoc train lai o day; script se dung embedding + feature crop mat "
            "de train binary classifier."
        )
    )
    parser.add_argument("--real-dataset", required=True, help="Thu muc anh that")
    parser.add_argument("--fake-dataset", required=True, help="Thu muc anh gia / AI")
    parser.add_argument("--output", default="reports/anti_spoof_training", help="Thu muc luu model va bao cao")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--val-size", type=float, default=0.2)
    parser.add_argument("--max-real", type=int, default=None)
    parser.add_argument("--max-fake", type=int, default=None)
    parser.add_argument("--learning-rate", type=float, default=0.05)
    parser.add_argument("--epochs", type=int, default=120)
    parser.add_argument("--l2", type=float, default=1e-4)
    parser.add_argument("--threshold-start", type=float, default=0.30)
    parser.add_argument("--threshold-end", type=float, default=0.80)
    parser.add_argument("--threshold-step", type=float, default=0.05)
    return parser.parse_args()


def collect_images(dataset_dir: Path, max_images=None):
    image_files = sorted(
        image_path
        for image_path in dataset_dir.iterdir()
        if image_path.is_file() and image_path.suffix.lower() in VALID_EXTENSIONS
    )
    if max_images is not None:
        image_files = image_files[:max_images]
    return image_files


def safe_div(numerator, denominator):
    return numerator / denominator if denominator else 0.0


def sigmoid(x):
    x = np.clip(x, -40.0, 40.0)
    return 1.0 / (1.0 + np.exp(-x))


def detect_and_crop_face_160(image_bytes):
    if face_utils.detector is None or face_utils.cv2 is None:
        raise RuntimeError("AI Models not initialized")

    nparr = face_utils.np.frombuffer(image_bytes, face_utils.np.uint8)
    img = face_utils.cv2.imdecode(nparr, face_utils.cv2.IMREAD_COLOR)
    if img is None:
        return None

    img_rgb = face_utils.cv2.cvtColor(img, face_utils.cv2.COLOR_BGR2RGB)
    results = face_utils.detector.detect_faces(img_rgb)
    if not results:
        return None

    results = [face for face in results if face["confidence"] >= face_utils.FACE_DETECTION_MIN_CONFIDENCE]
    if not results:
        return None

    best_face = max(results, key=lambda face: face["confidence"])
    return face_utils.preprocess_face(img_rgb, best_face["box"])


def extract_crop_statistics(face_rgb):
    gray = face_utils.cv2.cvtColor(face_rgb.astype("uint8"), face_utils.cv2.COLOR_RGB2GRAY)
    gray_float = gray.astype("float32") / 255.0

    gray_mean = float(np.mean(gray_float))
    gray_std = float(np.std(gray_float))

    rgb_mean = np.mean(face_rgb.astype("float32") / 255.0, axis=(0, 1))
    rgb_std = np.std(face_rgb.astype("float32") / 255.0, axis=(0, 1))

    lap_var = float(face_utils.cv2.Laplacian(gray, face_utils.cv2.CV_64F).var())
    edges = face_utils.cv2.Canny(gray, 80, 160)
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


def extract_feature_row(image_path: Path, label_name: str, target: int):
    image_bytes = image_path.read_bytes()
    started_at = time.perf_counter()
    embedding, error_message, diagnostics = validate_face_image(image_bytes)
    processing_time_ms = round((time.perf_counter() - started_at) * 1000.0, 2)
    diagnostics = diagnostics or {}

    base_row = {
        "path": str(image_path),
        "label_name": label_name,
        "target": target,
        "valid_face": embedding is not None,
        "reason": error_message or "ok",
        "processing_time_ms": processing_time_ms,
        "brightness_mean": diagnostics.get("brightness_mean"),
        "blur_variance": diagnostics.get("laplacian_variance"),
        "detector_confidence": diagnostics.get("face_confidence"),
        "relative_face_size": diagnostics.get("relative_face_size"),
        "yaw_score": diagnostics.get("yaw_score"),
    }

    if embedding is None:
        return None, base_row

    crop_face = detect_and_crop_face_160(image_bytes)
    if crop_face is None:
        base_row["valid_face"] = False
        base_row["reason"] = "crop_failed"
        return None, base_row

    crop_features = extract_crop_statistics(crop_face)
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
    feature_vector = np.concatenate([np.array(embedding, dtype="float32"), scalar_features, crop_features])
    return feature_vector, base_row


def build_dataset(real_paths, fake_paths):
    rows = []
    invalid_rows = []
    features = []
    labels = []

    for label_name, target, image_paths in (
        ("real", 1, real_paths),
        ("fake", 0, fake_paths),
    ):
        for image_path in image_paths:
            feature_vector, row = extract_feature_row(image_path, label_name, target)
            if feature_vector is None:
                invalid_rows.append(row)
                continue
            rows.append(row)
            features.append(feature_vector)
            labels.append(target)

    if not features:
        raise RuntimeError("Khong trich xuat duoc feature nao de train anti-spoof.")

    return np.vstack(features).astype("float32"), np.array(labels, dtype="float32"), rows, invalid_rows


def stratified_train_val_split(features, labels, rows, val_size, seed):
    grouped_indexes = {0: [], 1: []}
    for index, value in enumerate(labels):
        grouped_indexes[int(value)].append(index)

    rng = random.Random(seed)
    train_indexes = []
    val_indexes = []

    for indexes in grouped_indexes.values():
        rng.shuffle(indexes)
        val_count = max(1, int(math.ceil(len(indexes) * val_size)))
        if val_count >= len(indexes):
            val_count = len(indexes) - 1
        val_indexes.extend(indexes[:val_count])
        train_indexes.extend(indexes[val_count:])

    train_indexes = np.array(sorted(train_indexes))
    val_indexes = np.array(sorted(val_indexes))
    return (
        features[train_indexes],
        labels[train_indexes],
        [rows[i] for i in train_indexes],
        features[val_indexes],
        labels[val_indexes],
        [rows[i] for i in val_indexes],
    )


def standardize(train_x, val_x):
    mean = np.mean(train_x, axis=0)
    std = np.std(train_x, axis=0)
    std[std < 1e-6] = 1.0
    return (train_x - mean) / std, (val_x - mean) / std, mean, std


def train_logistic_regression(train_x, train_y, epochs, learning_rate, l2):
    num_features = train_x.shape[1]
    weights = np.zeros(num_features, dtype="float32")
    bias = 0.0
    history = []

    for epoch in range(epochs):
        logits = train_x @ weights + bias
        probs = sigmoid(logits)
        error = probs - train_y

        grad_w = (train_x.T @ error) / len(train_x) + l2 * weights
        grad_b = float(np.mean(error))

        weights -= learning_rate * grad_w
        bias -= learning_rate * grad_b

        eps = 1e-8
        loss = -np.mean(train_y * np.log(probs + eps) + (1.0 - train_y) * np.log(1.0 - probs + eps))
        loss += 0.5 * l2 * float(np.sum(weights * weights))
        history.append({"epoch": epoch + 1, "train_loss": float(loss)})

    return weights, bias, history


def predict_probabilities(features_x, weights, bias):
    return sigmoid(features_x @ weights + bias)


def compute_binary_metrics(y_true, probs, threshold):
    preds = (probs >= threshold).astype("int32")
    y_true = y_true.astype("int32")

    tp = int(np.sum((preds == 1) & (y_true == 1)))
    tn = int(np.sum((preds == 0) & (y_true == 0)))
    fp = int(np.sum((preds == 1) & (y_true == 0)))
    fn = int(np.sum((preds == 0) & (y_true == 1)))

    accuracy = safe_div(tp + tn, len(y_true))
    precision = safe_div(tp, tp + fp)
    recall = safe_div(tp, tp + fn)
    f1 = safe_div(2 * precision * recall, precision + recall)
    far = safe_div(fp, fp + tn)
    frr = safe_div(fn, fn + tp)
    tnr = safe_div(tn, fp + tn)
    balanced_accuracy = (recall + tnr) / 2.0
    acer = (far + frr) / 2.0

    return {
        "threshold": threshold,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "false_acceptance_rate": far,
        "false_rejection_rate": frr,
        "true_reject_rate": tnr,
        "balanced_accuracy": balanced_accuracy,
        "acer": acer,
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
    }


def threshold_sweep(y_true, probs, start, end, step):
    rows = []
    current = start
    while current <= end + 1e-9:
        threshold = round(current, 4)
        metrics = compute_binary_metrics(y_true, probs, threshold)
        metrics["meets_targets"] = (
            metrics["accuracy"] >= TARGET_ACCURACY
            and metrics["false_acceptance_rate"] < TARGET_FAR
            and metrics["false_rejection_rate"] < TARGET_FRR
        )
        rows.append(metrics)
        current += step
    return rows


def select_operating_point(sweep_rows):
    eligible = [row for row in sweep_rows if row["meets_targets"]]
    pool = eligible if eligible else sweep_rows
    best = min(
        pool,
        key=lambda item: (
            item["false_acceptance_rate"],
            -item["accuracy"],
            item["false_rejection_rate"],
            -item["balanced_accuracy"],
            item["threshold"],
        ),
    )
    return best


def write_json(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(path: Path, rows, fieldnames):
    with path.open("w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def build_report(summary):
    selected = summary["selected_operating_point"]
    lines = [
        "# Bao cao train anti-spoof model",
        "",
        "## Logic su dung trong du an",
        "- Bai toan recognition nguoi dung van dung FaceNet embedding.",
        "- Bai toan phan biet REAL / FAKE duoc train bang model anti-spoof rieng.",
        "- Pipeline de xuat: `Camera -> Face Detection -> Anti-Spoof -> FaceNet -> Compare`.",
        "",
        "## Cau hinh train",
        f"- Real dataset: `{summary['config']['real_dataset']}`",
        f"- Fake dataset: `{summary['config']['fake_dataset']}`",
        f"- So mau train: **{summary['dataset_overview']['train_samples']}**",
        f"- So mau validation: **{summary['dataset_overview']['val_samples']}**",
        f"- Feature size: **{summary['dataset_overview']['feature_dim']}**",
        f"- Epochs: **{summary['config']['epochs']}**",
        f"- Learning rate: **{summary['config']['learning_rate']}**",
        "",
        "## Chi so tai threshold mac dinh",
        f"- Accuracy: **{summary['default_metrics']['accuracy']:.4f}**",
        f"- Precision: **{summary['default_metrics']['precision']:.4f}**",
        f"- Recall: **{summary['default_metrics']['recall']:.4f}**",
        f"- F1-score: **{summary['default_metrics']['f1_score']:.4f}**",
        f"- FAR: **{summary['default_metrics']['false_acceptance_rate']:.4f}**",
        f"- FRR: **{summary['default_metrics']['false_rejection_rate']:.4f}**",
        f"- ACER: **{summary['default_metrics']['acer']:.4f}**",
        "",
        "## Operating point de xuat",
        f"- Threshold: **{selected['threshold']:.2f}**",
        f"- Accuracy: **{selected['accuracy']:.4f}**",
        f"- FAR: **{selected['false_acceptance_rate']:.4f}**",
        f"- FRR: **{selected['false_rejection_rate']:.4f}**",
        f"- Balanced Accuracy: **{selected['balanced_accuracy']:.4f}**",
        f"- Dat muc tieu Accuracy > {TARGET_ACCURACY:.2f}: **{'Co' if selected['accuracy'] >= TARGET_ACCURACY else 'Khong'}**",
        f"- Dat muc tieu FAR < {TARGET_FAR:.2f}: **{'Co' if selected['false_acceptance_rate'] < TARGET_FAR else 'Khong'}**",
        f"- Dat muc tieu FRR < {TARGET_FRR:.2f}: **{'Co' if selected['false_rejection_rate'] < TARGET_FRR else 'Khong'}**",
        "",
        "## Threshold sweep",
        "| Threshold | Accuracy | FAR | FRR | ACER | Balanced Acc | Dat muc tieu |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in summary["threshold_sweep"]:
        lines.append(
            f"| {row['threshold']:.2f} | {row['accuracy']:.4f} | {row['false_acceptance_rate']:.4f} | "
            f"{row['false_rejection_rate']:.4f} | {row['acer']:.4f} | {row['balanced_accuracy']:.4f} | "
            f"{'Co' if row['meets_targets'] else 'Khong'} |"
        )
    lines.extend(
        [
            "",
            "## Tep ket qua sinh ra",
            "- `summary.json`: Tong hop cau hinh va metric",
            "- `threshold_sweep.csv`: Bang chon threshold",
            "- `train_history.csv`: Lich su train logistic regression",
            "- `invalid_images.csv`: Anh bi loai truoc khi train",
            "- `anti_spoof_model.npz`: Trong so model + thong so standardization",
        ]
    )
    return "\n".join(lines)


def main():
    args = parse_args()
    output_dir = Path(args.output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    real_dataset = Path(args.real_dataset).resolve()
    fake_dataset = Path(args.fake_dataset).resolve()
    if not real_dataset.exists():
        raise FileNotFoundError(f"Khong tim thay real dataset: {real_dataset}")
    if not fake_dataset.exists():
        raise FileNotFoundError(f"Khong tim thay fake dataset: {fake_dataset}")

    real_paths = collect_images(real_dataset, args.max_real)
    fake_paths = collect_images(fake_dataset, args.max_fake)
    features, labels, rows, invalid_rows = build_dataset(real_paths, fake_paths)

    train_x, train_y, train_rows, val_x, val_y, val_rows = stratified_train_val_split(
        features,
        labels,
        rows,
        args.val_size,
        args.seed,
    )
    train_x, val_x, feature_mean, feature_std = standardize(train_x, val_x)

    weights, bias, history = train_logistic_regression(
        train_x,
        train_y,
        epochs=args.epochs,
        learning_rate=args.learning_rate,
        l2=args.l2,
    )
    val_probs = predict_probabilities(val_x, weights, bias)
    default_metrics = compute_binary_metrics(val_y, val_probs, 0.5)
    sweep_rows = threshold_sweep(val_y, val_probs, args.threshold_start, args.threshold_end, args.threshold_step)
    selected_point = select_operating_point(sweep_rows)

    summary = {
        "config": {
            "real_dataset": str(real_dataset),
            "fake_dataset": str(fake_dataset),
            "seed": args.seed,
            "val_size": args.val_size,
            "learning_rate": args.learning_rate,
            "epochs": args.epochs,
            "l2": args.l2,
        },
        "dataset_overview": {
            "raw_real_images": len(real_paths),
            "raw_fake_images": len(fake_paths),
            "valid_samples": int(len(rows)),
            "invalid_samples": int(len(invalid_rows)),
            "train_samples": int(len(train_rows)),
            "val_samples": int(len(val_rows)),
            "feature_dim": int(train_x.shape[1]),
        },
        "default_metrics": default_metrics,
        "threshold_sweep": sweep_rows,
        "selected_operating_point": selected_point,
    }

    np.savez_compressed(
        output_dir / "anti_spoof_model.npz",
        weights=weights.astype("float32"),
        bias=np.array([bias], dtype="float32"),
        feature_mean=feature_mean.astype("float32"),
        feature_std=feature_std.astype("float32"),
    )
    MODEL_EXPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(output_dir / "anti_spoof_model.npz", MODEL_EXPORT_PATH)
    write_json(output_dir / "summary.json", summary)
    write_csv(
        output_dir / "threshold_sweep.csv",
        sweep_rows,
        fieldnames=[
            "threshold",
            "accuracy",
            "precision",
            "recall",
            "f1_score",
            "false_acceptance_rate",
            "false_rejection_rate",
            "true_reject_rate",
            "balanced_accuracy",
            "acer",
            "tp",
            "tn",
            "fp",
            "fn",
            "meets_targets",
        ],
    )
    write_csv(output_dir / "train_history.csv", history, fieldnames=["epoch", "train_loss"])
    write_csv(
        output_dir / "invalid_images.csv",
        invalid_rows,
        fieldnames=[
            "path",
            "label_name",
            "target",
            "valid_face",
            "reason",
            "processing_time_ms",
            "brightness_mean",
            "blur_variance",
            "detector_confidence",
            "relative_face_size",
            "yaw_score",
        ],
    )
    (output_dir / "report.md").write_text(build_report(summary), encoding="utf-8")

    print("Train anti-spoof hoan tat.")
    print(f"Summary: {output_dir / 'summary.json'}")
    print(f"Model: {output_dir / 'anti_spoof_model.npz'}")
    print(f"Report: {output_dir / 'report.md'}")
    print(
        f"Selected threshold={selected_point['threshold']:.2f}, "
        f"accuracy={selected_point['accuracy']:.4f}, "
        f"FAR={selected_point['false_acceptance_rate']:.4f}, "
        f"FRR={selected_point['false_rejection_rate']:.4f}"
    )


if __name__ == "__main__":
    main()
