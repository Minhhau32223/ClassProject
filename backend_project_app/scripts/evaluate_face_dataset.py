import argparse
import csv
import json
import math
import random
import time
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apps import face_runtime as face_utils
from apps.face_runtime import (
    DEFAULT_FACE_MATCH_MARGIN,
    DEFAULT_FACE_MATCH_THRESHOLD,
    compare_faces,
    cosine_distance_between,
    get_average_embedding,
    get_embedding_from_image,
    validate_face_image,
)


VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
TARGET_ACCURACY = 0.85
TARGET_TOP1_ACCURACY = 0.90
TARGET_FAR = 0.20
TARGET_FRR = 0.10


@dataclass
class Sample:
    label: str
    path: Path


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Danh gia he thong backend theo 2 bai toan tach biet: "
            "(1) recognition tren dataset co nhan theo tung nguoi, "
            "(2) anti-spoof / do on dinh tren dataset phang REAL vs FAKE."
        )
    )
    parser.add_argument(
        "--dataset",
        "--recognition-eval",
        dest="dataset",
        help="Recognition eval: thu muc dataset co nhan theo cau truc dataset/person_a/*.jpg",
    )
    parser.add_argument(
        "--stability-datasets",
        "--antispoof-eval",
        nargs="+",
        dest="stability_datasets",
        help="Anti-spoof eval: danh sach dataset phang, nen truyen [REAL_IMAGES] [AI_GENERATED_IMAGES]",
    )
    parser.add_argument(
        "--pseudo-label-datasets",
        nargs="+",
        help="Che do tham do: dataset phang duoc gom cum thanh pseudo identity. Khong nen dung lam ket luan chinh trong bao cao.",
    )
    parser.add_argument("--output", default="reports/face_evaluation", help="Thu muc luu ket qua")
    parser.add_argument(
        "--crop-output",
        default="reports/face_evaluation/crops",
        help="Thu muc luu anh da cat 160x160 cho dataset phang",
    )
    parser.add_argument("--test-size", type=float, default=0.3, help="Ti le test cho moi lop")
    parser.add_argument("--threshold", type=float, default=DEFAULT_FACE_MATCH_THRESHOLD, help="Nguong cosine distance de chap nhan")
    parser.add_argument("--margin", type=float, default=DEFAULT_FACE_MATCH_MARGIN, help="Khoang cach toi thieu giua best match va second best")
    parser.add_argument("--seed", type=int, default=42, help="Seed de chia tap train/test")
    parser.add_argument("--max-classes", type=int, default=None, help="Gioi han so nguoi (class) duoc dua vao danh gia")
    parser.add_argument("--max-images-per-class", type=int, default=None, help="Gioi han so anh moi nguoi")
    parser.add_argument("--threshold-start", type=float, default=0.2, help="Threshold bat dau cho threshold sweep")
    parser.add_argument("--threshold-end", type=float, default=0.8, help="Threshold ket thuc cho threshold sweep")
    parser.add_argument("--threshold-step", type=float, default=0.05, help="Buoc nhay threshold cho threshold sweep")
    parser.add_argument("--gallery-images-per-class", type=int, default=3, help="So anh train dung de tao mau dang ky cho moi nguoi")
    parser.add_argument("--checkin-images-per-attempt", type=int, default=5, help="So anh test gom lai cho moi lan diem danh mo phong")
    parser.add_argument("--cluster-threshold", type=float, default=0.18, help="Nguong cosine distance de gom anh phang thanh cung mot nguoi")
    parser.add_argument("--cluster-refine-passes", type=int, default=2, help="So lan cap nhat lai centroid khi gom cum")
    parser.add_argument("--cluster-min-images", type=int, default=3, help="So anh toi thieu de mot cum duoc xem la mot nguoi hop le")
    parser.add_argument("--cluster-max-images", type=int, default=12, help="So anh toi da giu lai moi cum khi tao pseudo dataset")
    return parser.parse_args()


def find_class_directories(dataset_dir: Path):
    class_dirs = []
    for directory in sorted(dataset_dir.rglob("*")):
        if not directory.is_dir():
            continue
        has_image = any(
            child.is_file() and child.suffix.lower() in VALID_EXTENSIONS
            for child in directory.iterdir()
        )
        if has_image:
            class_dirs.append(directory)
    return class_dirs


def collect_samples(dataset_dir: Path, max_classes=None, max_images_per_class=None):
    samples = []
    class_dirs = find_class_directories(dataset_dir)

    if not class_dirs:
        return samples

    if max_classes is not None:
        class_dirs = class_dirs[:max_classes]

    for person_dir in class_dirs:
        image_files = sorted(
            image_path
            for image_path in person_dir.iterdir()
            if image_path.is_file() and image_path.suffix.lower() in VALID_EXTENSIONS
        )
        if max_images_per_class is not None:
            image_files = image_files[:max_images_per_class]

        for image_path in image_files:
            samples.append(Sample(label=person_dir.name, path=image_path))

    return samples


def collect_flat_images(dataset_dir: Path, max_images=None):
    image_files = sorted(
        image_path
        for image_path in dataset_dir.iterdir()
        if image_path.is_file() and image_path.suffix.lower() in VALID_EXTENSIONS
    )
    if max_images is not None:
        image_files = image_files[:max_images]
    return image_files


def stratified_split(samples, test_size, seed):
    grouped = defaultdict(list)
    for sample in samples:
        grouped[sample.label].append(sample)

    rng = random.Random(seed)
    train_samples = []
    test_samples = []

    for label, items in grouped.items():
        rng.shuffle(items)
        if len(items) < 2:
            raise ValueError(f"Lop '{label}' chi co {len(items)} anh, can it nhat 2 anh de train/test.")

        test_count = max(1, int(math.ceil(len(items) * test_size)))
        if test_count >= len(items):
            test_count = len(items) - 1

        test_samples.extend(items[:test_count])
        train_samples.extend(items[test_count:])

    return train_samples, test_samples


def extract_embedding(image_path: Path):
    image_bytes = image_path.read_bytes()
    return get_embedding_from_image(image_bytes)


def build_attendance_gallery(train_samples, gallery_images_per_class):
    grouped_samples = defaultdict(list)
    invalid_images = []
    gallery_sources = {}

    for sample in train_samples:
        grouped_samples[sample.label].append(sample)

    gallery = {}
    for label, items in grouped_samples.items():
        embeddings = []
        valid_paths = []
        for sample in items[:gallery_images_per_class]:
            embedding = extract_embedding(sample.path)
            if embedding is None:
                invalid_images.append(
                    {
                        "split": "train",
                        "label": label,
                        "path": str(sample.path),
                        "reason": "no_face_detected",
                    }
                )
                continue
            embeddings.append(embedding)
            valid_paths.append(str(sample.path))

        if embeddings:
            gallery[label] = get_average_embedding(embeddings)
            gallery_sources[label] = valid_paths

    return gallery, invalid_images, gallery_sources


def build_checkin_attempts(test_samples, checkin_images_per_attempt):
    grouped = defaultdict(list)
    for sample in test_samples:
        grouped[sample.label].append(sample)

    attempts = []
    for label, items in grouped.items():
        for index in range(0, len(items), checkin_images_per_attempt):
            chunk = items[index:index + checkin_images_per_attempt]
            if not chunk:
                continue
            attempts.append(
                {
                    "label": label,
                    "samples": chunk,
                    "attempt_id": f"{label}_{index // checkin_images_per_attempt + 1}",
                }
            )
    return attempts


def aggregate_attempt_embedding(attempt):
    embeddings = []
    invalid_samples = []
    valid_paths = []

    for sample in attempt["samples"]:
        embedding = extract_embedding(sample.path)
        if embedding is None:
            invalid_samples.append(
                {
                    "split": "test",
                    "label": attempt["label"],
                    "path": str(sample.path),
                    "reason": "no_face_detected",
                }
            )
            continue
        embeddings.append(embedding)
        valid_paths.append(str(sample.path))

    if not embeddings:
        return None, invalid_samples, valid_paths

    return get_average_embedding(embeddings), invalid_samples, valid_paths


def predict_attendance_identity(embedding, gallery, threshold, margin):
    candidates = []
    for label, reference_embedding in gallery.items():
        distance = cosine_distance_between(embedding, reference_embedding)
        candidates.append({"label": label, "distance": float(distance)})

    if not candidates:
        return "unknown", None, False, "unknown", {}, None, False

    candidates.sort(key=lambda item: item["distance"])
    best = candidates[0]
    second_best = candidates[1] if len(candidates) > 1 else None
    best_distance = best["distance"]
    top1_label = best["label"]
    all_distances = {item["label"]: item["distance"] for item in candidates}
    margin_value = second_best["distance"] - best_distance if second_best else None
    passes_threshold = best_distance < threshold
    passes_margin = second_best is None or margin_value >= margin
    accepted = passes_threshold and passes_margin
    predicted_label = top1_label if accepted else "unknown"
    return predicted_label, best_distance, accepted, top1_label, all_distances, margin_value, passes_margin


def evaluate_attendance_attempts(attempts, gallery, threshold, margin):
    y_true = []
    y_pred = []
    y_top1_pred = []
    invalid_images = []
    predictions = []

    for attempt in attempts:
        y_true.append(attempt["label"])
        aggregate_embedding, invalid_samples, valid_paths = aggregate_attempt_embedding(attempt)
        invalid_images.extend(invalid_samples)

        if aggregate_embedding is None:
            y_pred.append("unknown")
            y_top1_pred.append("unknown")
            predictions.append(
                {
                    "attempt_id": attempt["attempt_id"],
                    "path": "; ".join(str(sample.path) for sample in attempt["samples"]),
                    "true_label": attempt["label"],
                    "predicted_label": "unknown",
                    "top1_label": "unknown",
                    "distance": None,
                    "accepted": False,
                    "reason": "no_valid_frames",
                    "distances": {},
                    "valid_frames": 0,
                    "total_frames": len(attempt["samples"]),
                    "margin": None,
                    "passes_margin": False,
                }
            )
            continue

        predicted_label, distance, accepted, top1_label, all_distances, margin_value, passes_margin = predict_attendance_identity(
            aggregate_embedding,
            gallery,
            threshold,
            margin,
        )
        y_pred.append(predicted_label)
        y_top1_pred.append(top1_label if top1_label is not None else "unknown")
        predictions.append(
            {
                "attempt_id": attempt["attempt_id"],
                "path": "; ".join(valid_paths),
                "true_label": attempt["label"],
                "predicted_label": predicted_label,
                "top1_label": top1_label if top1_label is not None else "unknown",
                "distance": float(distance) if distance is not None else None,
                "accepted": accepted,
                "reason": "ok",
                "distances": all_distances,
                "valid_frames": len(valid_paths),
                "total_frames": len(attempt["samples"]),
                "margin": float(margin_value) if margin_value is not None else None,
                "passes_margin": passes_margin,
            }
        )

    return y_true, y_pred, y_top1_pred, invalid_images, predictions


def sanitize_name(value: str):
    return "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in value).strip("_") or "dataset"


def detect_and_crop_face_160(image_bytes):
    if face_utils.detector is None or face_utils.cv2 is None:
        raise RuntimeError("AI Models not initialized")

    nparr = face_utils.np.frombuffer(image_bytes, face_utils.np.uint8)
    img = face_utils.cv2.imdecode(nparr, face_utils.cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Invalid image")

    img_rgb = face_utils.cv2.cvtColor(img, face_utils.cv2.COLOR_BGR2RGB)
    results = face_utils.detector.detect_faces(img_rgb)
    if not results:
        return None, None

    results = [face for face in results if face["confidence"] >= face_utils.FACE_DETECTION_MIN_CONFIDENCE]
    if not results:
        return None, None

    best_face = max(results, key=lambda face: face["confidence"])
    x, y, w, h = best_face["box"]
    if w <= 0 or h <= 0:
        return None, None

    face = face_utils.preprocess_face(img_rgb, best_face["box"])
    if face is None:
        return None, None

    image_height, image_width = img_rgb.shape[:2]
    diagnostics = {
        "face_confidence": float(best_face["confidence"]),
        "face_width": int(w),
        "face_height": int(h),
        "relative_face_size": max(float(w / image_width), float(h / image_height)),
    }
    return face, diagnostics


def analyze_unlabeled_images(image_paths, crop_output_dir=None):
    rows = []
    invalid_images = []
    reason_counts = Counter()
    valid_count = 0
    confidence_values = []
    brightness_values = []
    blur_values = []
    relative_face_size_values = []
    processing_times = []
    crop_failures = 0

    if crop_output_dir is not None:
        crop_output_dir.mkdir(parents=True, exist_ok=True)

    for image_path in image_paths:
        image_bytes = image_path.read_bytes()
        started_at = time.perf_counter()
        embedding, error_message, diagnostics = validate_face_image(image_bytes)
        processing_times.append(time.perf_counter() - started_at)
        diagnostics = diagnostics or {}
        row = {
            "path": str(image_path),
            "valid_face": embedding is not None,
            "reason": error_message or "ok",
            "detector_confidence": diagnostics.get("face_confidence"),
            "brightness_mean": diagnostics.get("brightness_mean"),
            "blur_variance": diagnostics.get("laplacian_variance"),
            "relative_face_size": diagnostics.get("relative_face_size"),
            "face_width": diagnostics.get("face_width"),
            "face_height": diagnostics.get("face_height"),
            "processing_time_ms": round(processing_times[-1] * 1000, 2),
            "crop_saved": False,
        }
        rows.append(row)

        if embedding is not None:
            valid_count += 1
            if diagnostics.get("face_confidence") is not None:
                confidence_values.append(float(diagnostics["face_confidence"]))
            if diagnostics.get("brightness_mean") is not None:
                brightness_values.append(float(diagnostics["brightness_mean"]))
            if diagnostics.get("laplacian_variance") is not None:
                blur_values.append(float(diagnostics["laplacian_variance"]))
            if diagnostics.get("relative_face_size") is not None:
                relative_face_size_values.append(float(diagnostics["relative_face_size"]))
            else:
                face_width = diagnostics.get("face_width")
                face_height = diagnostics.get("face_height")
                if face_width and face_height:
                    crop_info = detect_and_crop_face_160(image_bytes)[1]
                    if crop_info and crop_info.get("relative_face_size") is not None:
                        relative_face_size_values.append(float(crop_info["relative_face_size"]))

            if crop_output_dir is not None:
                crop_face, crop_info = detect_and_crop_face_160(image_bytes)
                if crop_face is not None:
                    crop_filename = f"{image_path.stem}_face160.jpg"
                    crop_path = crop_output_dir / crop_filename
                    face_bgr = face_utils.cv2.cvtColor(crop_face, face_utils.cv2.COLOR_RGB2BGR)
                    face_utils.cv2.imwrite(str(crop_path), face_bgr)
                    row["crop_saved"] = True
                    row["crop_path"] = str(crop_path)
                    if row["detector_confidence"] is None and crop_info:
                        row["detector_confidence"] = crop_info.get("face_confidence")
                    if row["relative_face_size"] is None and crop_info:
                        row["relative_face_size"] = crop_info.get("relative_face_size")
                else:
                    crop_failures += 1
        else:
            reason = error_message or "unknown_error"
            reason_counts[reason] += 1
            invalid_images.append(
                {
                    "split": "flat_dataset",
                    "label": "unknown",
                    "path": str(image_path),
                    "reason": reason,
                    "meta": diagnostics,
                }
            )

    total_images = len(image_paths)
    invalid_count = total_images - valid_count

    def mean_or_zero(values):
        return float(np.mean(values)) if values else 0.0

    summary = {
        "dataset_type": "unlabeled_flat_images",
        "dataset_overview": {
            "num_classes": 0,
            "num_images": total_images,
            "valid_face_images": valid_count,
            "invalid_images": invalid_count,
            "face_detection_rate": safe_div(valid_count, total_images),
            "invalid_reason_counts": dict(sorted(reason_counts.items())),
        },
        "quality_metrics": {
            "average_detector_confidence": mean_or_zero(confidence_values),
            "average_brightness_mean": mean_or_zero(brightness_values),
            "average_blur_variance": mean_or_zero(blur_values),
            "average_relative_face_size": mean_or_zero(relative_face_size_values),
            "average_processing_time_ms": mean_or_zero(processing_times) * 1000,
            "crop_success_rate": safe_div(valid_count - crop_failures, valid_count),
        },
    }
    return summary, rows, invalid_images


def compare_flat_datasets(dataset_dirs, crop_root_dir, max_images_per_dataset=None):
    comparison_rows = []
    summaries = []

    for dataset_dir in dataset_dirs:
        image_paths = collect_flat_images(dataset_dir, max_images_per_dataset)
        dataset_output_dir = crop_root_dir / sanitize_name(dataset_dir.name)
        summary, quality_rows, invalid_images = analyze_unlabeled_images(image_paths, dataset_output_dir)
        summary["dataset"] = str(dataset_dir)
        summary["dataset_name"] = dataset_dir.name
        summaries.append(
            {
                "summary": summary,
                "quality_rows": quality_rows,
                "invalid_images": invalid_images,
                "crop_dir": str(dataset_output_dir),
            }
        )
        comparison_rows.append(
            {
                "dataset_name": dataset_dir.name,
                "dataset_path": str(dataset_dir),
                "num_images": summary["dataset_overview"]["num_images"],
                "valid_face_images": summary["dataset_overview"]["valid_face_images"],
                "invalid_images": summary["dataset_overview"]["invalid_images"],
                "face_detection_rate": summary["dataset_overview"]["face_detection_rate"],
                "average_detector_confidence": summary["quality_metrics"]["average_detector_confidence"],
                "average_brightness_mean": summary["quality_metrics"]["average_brightness_mean"],
                "average_blur_variance": summary["quality_metrics"]["average_blur_variance"],
                "average_relative_face_size": summary["quality_metrics"]["average_relative_face_size"],
                "average_processing_time_ms": summary["quality_metrics"]["average_processing_time_ms"],
                "crop_success_rate": summary["quality_metrics"]["crop_success_rate"],
            }
        )

    return summaries, comparison_rows


def collect_valid_flat_embeddings(image_paths):
    valid_entries = []
    invalid_images = []
    quality_rows = []

    for image_path in image_paths:
        image_bytes = image_path.read_bytes()
        started_at = time.perf_counter()
        embedding, error_message, diagnostics = validate_face_image(image_bytes)
        processing_time_ms = round((time.perf_counter() - started_at) * 1000, 2)
        diagnostics = diagnostics or {}
        quality_rows.append(
            {
                "path": str(image_path),
                "valid_face": embedding is not None,
                "reason": error_message or "ok",
                "detector_confidence": diagnostics.get("face_confidence"),
                "brightness_mean": diagnostics.get("brightness_mean"),
                "blur_variance": diagnostics.get("laplacian_variance"),
                "relative_face_size": diagnostics.get("relative_face_size"),
                "face_width": diagnostics.get("face_width"),
                "face_height": diagnostics.get("face_height"),
                "processing_time_ms": processing_time_ms,
            }
        )

        if embedding is None:
            invalid_images.append(
                {
                    "path": str(image_path),
                    "reason": error_message or "unknown_error",
                    "meta": diagnostics,
                }
            )
            continue

        valid_entries.append(
            {
                "path": image_path,
                "embedding": embedding,
                "diagnostics": diagnostics,
                "processing_time_ms": processing_time_ms,
            }
        )

    return valid_entries, invalid_images, quality_rows


def compute_cluster_centroid(items):
    return get_average_embedding([item["embedding"] for item in items])


def cluster_flat_embeddings(valid_entries, distance_threshold, refine_passes=2):
    if not valid_entries:
        return []

    clusters = []
    for entry in valid_entries:
        if not clusters:
            clusters.append({"items": [entry], "centroid": entry["embedding"]})
            continue

        best_cluster = None
        best_distance = None
        for cluster in clusters:
            distance = cosine_distance_between(entry["embedding"], cluster["centroid"])
            if best_distance is None or distance < best_distance:
                best_distance = distance
                best_cluster = cluster

        if best_cluster is not None and best_distance is not None and best_distance <= distance_threshold:
            best_cluster["items"].append(entry)
            best_cluster["centroid"] = compute_cluster_centroid(best_cluster["items"])
        else:
            clusters.append({"items": [entry], "centroid": entry["embedding"]})

    for _ in range(max(0, refine_passes)):
        centroids = [cluster["centroid"] for cluster in clusters]
        reassigned = [[] for _ in clusters]

        for entry in valid_entries:
            best_index = None
            best_distance = None
            for index, centroid in enumerate(centroids):
                distance = cosine_distance_between(entry["embedding"], centroid)
                if best_distance is None or distance < best_distance:
                    best_distance = distance
                    best_index = index

            if best_index is not None and best_distance is not None and best_distance <= distance_threshold:
                reassigned[best_index].append(entry)
            else:
                reassigned.append([entry])
                centroids.append(entry["embedding"])

        rebuilt_clusters = []
        for items in reassigned:
            if not items:
                continue
            rebuilt_clusters.append({"items": items, "centroid": compute_cluster_centroid(items)})
        clusters = rebuilt_clusters

    normalized_clusters = []
    for index, cluster in enumerate(sorted(clusters, key=lambda item: len(item["items"]), reverse=True), start=1):
        items = sorted(cluster["items"], key=lambda item: str(item["path"]))
        intra_distances = []
        for left in range(len(items)):
            for right in range(left + 1, len(items)):
                intra_distances.append(
                    cosine_distance_between(items[left]["embedding"], items[right]["embedding"])
                )

        normalized_clusters.append(
            {
                "cluster_id": f"cluster_{index:04d}",
                "size": len(items),
                "centroid": cluster["centroid"],
                "items": items,
                "avg_intra_distance": float(np.mean(intra_distances)) if intra_distances else 0.0,
                "max_intra_distance": max(intra_distances) if intra_distances else 0.0,
            }
        )

    return normalized_clusters


def build_samples_from_clusters(clusters, min_images, max_images):
    samples = []
    cluster_rows = []

    for cluster in clusters:
        kept_items = cluster["items"][:max_images] if max_images is not None else cluster["items"]
        eligible = len(kept_items) >= min_images
        cluster_rows.append(
            {
                "cluster_id": cluster["cluster_id"],
                "cluster_size": cluster["size"],
                "used_images": len(kept_items) if eligible else 0,
                "eligible": eligible,
                "avg_intra_distance": cluster["avg_intra_distance"],
                "max_intra_distance": cluster["max_intra_distance"],
                "example_path": str(cluster["items"][0]["path"]) if cluster["items"] else "",
            }
        )
        if not eligible:
            continue

        for item in kept_items:
            samples.append(Sample(label=cluster["cluster_id"], path=item["path"]))

    return samples, cluster_rows


def recognition_target_status(metrics):
    return {
        "target_accuracy": TARGET_ACCURACY,
        "target_top1_accuracy": TARGET_TOP1_ACCURACY,
        "target_far": TARGET_FAR,
        "target_frr": TARGET_FRR,
        "meets_accuracy": metrics.get("accuracy", 0.0) >= TARGET_ACCURACY,
        "meets_top1_accuracy": metrics.get("top1_accuracy", 0.0) >= TARGET_TOP1_ACCURACY,
        "meets_far": metrics.get("false_acceptance_rate", 1.0) < TARGET_FAR,
        "meets_frr": metrics.get("false_rejection_rate", 1.0) < TARGET_FRR,
    }


def select_operating_point(sweep_rows):
    if not sweep_rows:
        return None

    eligible = [
        item
        for item in sweep_rows
        if item.get("accuracy", 0.0) >= TARGET_ACCURACY
        and item.get("top1_accuracy", 0.0) >= TARGET_TOP1_ACCURACY
        and item.get("false_acceptance_rate", 1.0) < TARGET_FAR
        and item.get("false_rejection_rate", 1.0) < TARGET_FRR
    ]

    candidate_pool = eligible if eligible else sweep_rows
    best = min(
        candidate_pool,
        key=lambda item: (
            item["false_acceptance_rate"],
            -item["accuracy"],
            -item.get("top1_accuracy", 0.0),
            item["false_rejection_rate"],
            item["threshold"],
        ),
    )
    best["meets_all_targets"] = best in eligible
    best["target_status"] = recognition_target_status(best)
    return best


def evaluate_recognition_dataset(samples, args, dataset_name, dataset_path):
    label_counts = Counter(sample.label for sample in samples)
    train_samples, test_samples = stratified_split(samples, args.test_size, args.seed)

    gallery, invalid_train, gallery_sources = build_attendance_gallery(
        train_samples,
        args.gallery_images_per_class,
    )
    if not gallery:
        raise RuntimeError("Khong tao duoc gallery train tu pseudo-labeled dataset.")

    attempts = build_checkin_attempts(test_samples, args.checkin_images_per_attempt)
    y_true, y_pred, y_top1_pred, invalid_test, predictions = evaluate_attendance_attempts(
        attempts,
        gallery,
        args.threshold,
        args.margin,
    )
    labels = sorted(gallery.keys())
    metrics = classification_metrics(y_true, y_pred, labels)
    top1_metrics = top1_accuracy(y_true, y_top1_pred)
    verification = verification_metrics(predictions, labels, args.threshold)
    sweep = threshold_sweep(
        predictions,
        labels,
        args.threshold_start,
        args.threshold_end,
        args.threshold_step,
        args.margin,
    )
    for item in sweep:
        item["top1_accuracy"] = top1_metrics["top1_accuracy"]
    selected_point = select_operating_point(sweep)
    matrix_labels, matrix_rows = confusion_matrix(y_true, y_pred, labels)
    invalid_images = invalid_train + invalid_test

    summary = {
        "dataset_type": "pseudo_labeled_recognition",
        "dataset": str(dataset_path),
        "dataset_name": dataset_name,
        "config": {
            "test_size": args.test_size,
            "threshold": args.threshold,
            "margin": args.margin,
            "seed": args.seed,
            "gallery_images_per_class": args.gallery_images_per_class,
            "checkin_images_per_attempt": args.checkin_images_per_attempt,
            "threshold_start": args.threshold_start,
            "threshold_end": args.threshold_end,
            "threshold_step": args.threshold_step,
        },
        "dataset_overview": {
            "num_classes": len(label_counts),
            "num_images": len(samples),
            "images_per_class": dict(sorted(label_counts.items())),
            "train_images": len(train_samples),
            "train_valid": sum(1 for sample in train_samples if sample.label in gallery),
            "test_images": len(test_samples),
            "checkin_attempts": len(attempts),
            "invalid_images": len(invalid_images),
        },
        "metrics": metrics,
        "top1_metrics": top1_metrics,
        "verification": verification,
        "threshold_sweep": sweep,
        "selected_operating_point": selected_point,
        "target_status": recognition_target_status(
            {
                "accuracy": metrics["accuracy"],
                "top1_accuracy": top1_metrics["top1_accuracy"],
                "false_acceptance_rate": verification["false_acceptance_rate"],
                "false_rejection_rate": verification["false_rejection_rate"],
            }
        ),
        "gallery_classes": labels,
        "gallery_strategy": "average_of_registration_frames_per_person",
        "checkin_strategy": f"{args.checkin_images_per_attempt}_frame_average_embedding_with_best_match_margin",
        "gallery_sources": gallery_sources,
    }
    return summary, predictions, matrix_labels, matrix_rows, invalid_images


def build_liveness_metrics(comparison_rows):
    if len(comparison_rows) != 2:
        return None

    live = comparison_rows[0]
    spoof = comparison_rows[1]

    tp = int(live["valid_face_images"])
    fn = int(live["invalid_images"])
    fp = int(spoof["valid_face_images"])
    tn = int(spoof["invalid_images"])

    tar = safe_div(tp, tp + fn)
    frr = safe_div(fn, tp + fn)
    far = safe_div(fp, fp + tn)
    tnr = safe_div(tn, fp + tn)
    precision = safe_div(tp, tp + fp)
    recall = tar
    f1 = safe_div(2 * precision * recall, precision + recall)
    acer = (far + frr) / 2.0
    balanced_accuracy = (tar + tnr) / 2.0

    return {
        "assumption": "dataset_1=live_real_faces, dataset_2=spoof_ai_faces",
        "live_dataset": live["dataset_name"],
        "spoof_dataset": spoof["dataset_name"],
        "true_positive_live_accepts": tp,
        "false_negative_live_rejects": fn,
        "false_positive_spoof_accepts": fp,
        "true_negative_spoof_rejects": tn,
        "true_accept_rate": tar,
        "false_reject_rate": frr,
        "false_accept_rate": far,
        "true_reject_rate": tnr,
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "acer": acer,
        "balanced_accuracy": balanced_accuracy,
    }


def build_gallery(train_samples):
    grouped_embeddings = defaultdict(list)
    invalid_images = []
    gallery_sources = {}

    for sample in train_samples:
        embedding = extract_embedding(sample.path)
        if embedding is None:
            invalid_images.append(
                {
                    "split": "train",
                    "label": sample.label,
                    "path": str(sample.path),
                    "reason": "no_face_detected",
                }
            )
            continue
        grouped_embeddings[sample.label].append(embedding)
        if sample.label not in gallery_sources:
            gallery_sources[sample.label] = str(sample.path)

    gallery = {}
    for label, embeddings in grouped_embeddings.items():
        if embeddings:
            # Danh gia theo kich ban "moi nguoi 1 anh dai dien":
            # lay embedding hop le dau tien trong tap train lam gallery.
            gallery[label] = embeddings[0]

    return gallery, invalid_images, gallery_sources


def predict_label(embedding, gallery, threshold):
    best_label = None
    best_distance = None
    all_distances = {}

    for label, reference_embedding in gallery.items():
        _, distance = compare_faces(embedding, reference_embedding, threshold=threshold)
        all_distances[label] = float(distance)
        if best_distance is None or distance < best_distance:
            best_distance = distance
            best_label = label

    accepted = best_distance is not None and best_distance < threshold
    predicted_label = best_label if accepted else "unknown"
    top1_label = best_label
    return predicted_label, best_distance, accepted, top1_label, all_distances


def safe_div(numerator, denominator):
    return numerator / denominator if denominator else 0.0


def evaluate(test_samples, gallery, threshold):
    y_true = []
    y_pred = []
    y_top1_pred = []
    invalid_images = []
    predictions = []

    for sample in test_samples:
        embedding = extract_embedding(sample.path)
        if embedding is None:
            invalid_images.append(
                {
                    "split": "test",
                    "label": sample.label,
                    "path": str(sample.path),
                    "reason": "no_face_detected",
                }
            )
            y_true.append(sample.label)
            y_pred.append("unknown")
            y_top1_pred.append("unknown")
            predictions.append(
                {
                    "path": str(sample.path),
                    "true_label": sample.label,
                    "predicted_label": "unknown",
                    "top1_label": "unknown",
                    "distance": None,
                    "accepted": False,
                    "reason": "no_face_detected",
                    "distances": {},
                }
            )
            continue

        predicted_label, distance, accepted, top1_label, all_distances = predict_label(embedding, gallery, threshold)
        y_true.append(sample.label)
        y_pred.append(predicted_label)
        y_top1_pred.append(top1_label if top1_label is not None else "unknown")
        predictions.append(
            {
                "path": str(sample.path),
                "true_label": sample.label,
                "predicted_label": predicted_label,
                "top1_label": top1_label if top1_label is not None else "unknown",
                "distance": float(distance) if distance is not None else None,
                "accepted": accepted,
                "reason": "ok",
                "distances": all_distances,
            }
        )

    return y_true, y_pred, y_top1_pred, invalid_images, predictions


def classification_metrics(y_true, y_pred, labels):
    per_class = {}
    correct = sum(1 for truth, pred in zip(y_true, y_pred) if truth == pred)
    total = len(y_true)

    for label in labels:
        tp = sum(1 for truth, pred in zip(y_true, y_pred) if truth == label and pred == label)
        fp = sum(1 for truth, pred in zip(y_true, y_pred) if truth != label and pred == label)
        fn = sum(1 for truth, pred in zip(y_true, y_pred) if truth == label and pred != label)
        precision = safe_div(tp, tp + fp)
        recall = safe_div(tp, tp + fn)
        f1 = safe_div(2 * precision * recall, precision + recall)
        support = sum(1 for truth in y_true if truth == label)
        per_class[label] = {
            "precision": precision,
            "recall": recall,
            "f1_score": f1,
            "support": support,
        }

    macro_precision = safe_div(sum(item["precision"] for item in per_class.values()), len(labels))
    macro_recall = safe_div(sum(item["recall"] for item in per_class.values()), len(labels))
    macro_f1 = safe_div(sum(item["f1_score"] for item in per_class.values()), len(labels))

    return {
        "accuracy": safe_div(correct, total),
        "macro_precision": macro_precision,
        "macro_recall": macro_recall,
        "macro_f1": macro_f1,
        "total_test_samples": total,
        "correct_predictions": correct,
        "per_class": per_class,
    }


def top1_accuracy(y_true, y_top1_pred):
    correct = sum(1 for truth, pred in zip(y_true, y_top1_pred) if truth == pred)
    total = len(y_true)
    return {
        "top1_accuracy": safe_div(correct, total),
        "correct_top1_predictions": correct,
        "total_test_samples": total,
    }


def confusion_matrix(y_true, y_pred, labels):
    matrix = []
    ordered_labels = list(labels) + ["unknown"]

    for true_label in ordered_labels:
        row = {"true_label": true_label}
        for predicted_label in ordered_labels:
            row[predicted_label] = sum(
                1
                for truth, pred in zip(y_true, y_pred)
                if truth == true_label and pred == predicted_label
            )
        matrix.append(row)

    return ordered_labels, matrix


def verification_metrics(predictions, gallery_labels, threshold):
    false_reject = 0
    false_accept = 0
    genuine_total = 0
    impostor_total = 0

    for prediction in predictions:
        if prediction["reason"] != "ok":
            continue

        distances = prediction["distances"]
        true_label = prediction["true_label"]

        if true_label in distances:
            genuine_total += 1
            if distances[true_label] >= threshold:
                false_reject += 1

        for label in gallery_labels:
            if label == true_label or label not in distances:
                continue
            impostor_total += 1
            if distances[label] < threshold:
                false_accept += 1

    return {
        "threshold": threshold,
        "false_rejection_rate": safe_div(false_reject, genuine_total),
        "false_acceptance_rate": safe_div(false_accept, impostor_total),
        "genuine_attempts": genuine_total,
        "impostor_attempts": impostor_total,
        "false_rejects": false_reject,
        "false_accepts": false_accept,
    }


def threshold_sweep(predictions, gallery_labels, start, end, step, margin):
    thresholds = []
    current = start
    while current <= end + 1e-9:
        threshold = round(current, 4)
        threshold_predictions = []
        y_true = []
        y_pred = []

        for prediction in predictions:
            true_label = prediction["true_label"]
            y_true.append(true_label)

            if prediction["reason"] != "ok":
                y_pred.append("unknown")
                threshold_predictions.append(
                    {
                        **prediction,
                        "predicted_label": "unknown",
                        "accepted": False,
                    }
                )
                continue

            distances = prediction["distances"]
            if distances:
                best_label = min(distances, key=distances.get)
                best_distance = distances[best_label]
                second_best_distance = None
                if len(distances) > 1:
                    ordered = sorted(distances.items(), key=lambda item: item[1])
                    second_best_distance = ordered[1][1]
                accepted = best_distance < threshold and (
                    second_best_distance is None or (second_best_distance - best_distance) >= margin
                )
                predicted_label = best_label if accepted else "unknown"
            else:
                predicted_label = "unknown"
                accepted = False

            y_pred.append(predicted_label)
            threshold_predictions.append(
                {
                    **prediction,
                    "predicted_label": predicted_label,
                    "accepted": accepted,
                }
            )

        metrics = classification_metrics(y_true, y_pred, gallery_labels)
        verification = verification_metrics(threshold_predictions, gallery_labels, threshold)
        thresholds.append(
            {
                "threshold": threshold,
                "accuracy": metrics["accuracy"],
                "macro_precision": metrics["macro_precision"],
                "macro_recall": metrics["macro_recall"],
                "macro_f1": metrics["macro_f1"],
                "false_acceptance_rate": verification["false_acceptance_rate"],
                "false_rejection_rate": verification["false_rejection_rate"],
                "margin": margin,
            }
        )
        current += step

    return thresholds


def write_json(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(path: Path, rows, fieldnames):
    with path.open("w", newline="", encoding="utf-8-sig") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def build_markdown_report(summary):
    if summary.get("dataset_type") == "flat_dataset_comparison":
        lines = [
            "# Bao cao do on dinh pipeline backend",
            "",
            "## Dataset so sanh",
        ]
        for item in summary["datasets"]:
            lines.append(f"- `{item['dataset_name']}`: `{item['dataset']}`")
        lines.extend(
            [
                "",
                "## Tong hop ket qua",
                "| Dataset | So anh | Anh hop le | Ty le hop le | Crop 160x160 thanh cong | TG xu ly TB (ms) |",
                "| --- | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for item in summary["comparison"]:
            lines.append(
                f"| {item['dataset_name']} | {item['num_images']} | {item['valid_face_images']} | "
                f"{item['face_detection_rate']:.4f} | {item['crop_success_rate']:.4f} | "
                f"{item['average_processing_time_ms']:.2f} |"
            )
        if summary.get("liveness_metrics"):
            metrics = summary["liveness_metrics"]
            lines.extend(
                [
                    "",
                    "## Chi so ky thuat live/spoof",
                    f"- TAR / Recall: **{metrics['true_accept_rate']:.4f}**",
                    f"- FRR: **{metrics['false_reject_rate']:.4f}**",
                    f"- FAR / APCER: **{metrics['false_accept_rate']:.4f}**",
                    f"- TNR / BPCER-bo-sung: **{metrics['true_reject_rate']:.4f}**",
                    f"- Precision: **{metrics['precision']:.4f}**",
                    f"- F1-score: **{metrics['f1_score']:.4f}**",
                    f"- ACER: **{metrics['acer']:.4f}**",
                    f"- Balanced Accuracy: **{metrics['balanced_accuracy']:.4f}**",
                ]
            )
        lines.extend(
            [
                "",
                "## Nhan xet",
                "- Ty le hop le cao hon cho thay pipeline backend phat hien va xu ly khuon mat on dinh hon tren dataset do.",
                "- `crop_success_rate` phan anh kha nang cat mat 160x160 thanh cong sau khi anh da du dieu kien backend.",
                "- Neu hai dataset co chenhlech lon, can xem lai nguong loc chat luong anh va kha nang tong quat cua detector.",
                "- Neu coi `Real Images` la live va `AI-Generated Images` la spoof, thi bo chi so live/spoof giup danh gia muc do an toan khi diem danh.",
                "- Day la bai toan anti-spoof / live-vs-fake, khong phai recognition identity.",
                "",
                "## Tep ket qua sinh ra",
                "- `comparison_summary.json`: Tong hop so sanh giua cac dataset",
                "- `comparison.csv`: Bang chi so tong hop",
                "- `crops/`: Anh mat da cat 160x160",
            ]
        )
        return "\n".join(lines)

    if summary.get("dataset_type") == "pseudo_labeled_recognition":
        selected_point = summary.get("selected_operating_point") or {}
        target_status = summary.get("target_status") or {}
        selected_target_status = selected_point.get("target_status") or {}
        lines = [
            "# Bao cao recognition tu dataset phang da gom cum",
            "",
            "## Cau hinh chay",
            f"- Dataset goc: `{summary['dataset']}`",
            f"- So nguoi gia lap sau gom cum: **{summary['dataset_overview']['num_classes']}**",
            f"- So anh duoc dua vao recognition eval: **{summary['dataset_overview']['num_images']}**",
            f"- Threshold danh gia hien tai: **{summary['config']['threshold']}**",
            f"- Margin best match: **{summary['config']['margin']}**",
            f"- Anh dang ky / nguoi: **{summary['config']['gallery_images_per_class']}**",
            f"- Anh diem danh / lan thu: **{summary['config']['checkin_images_per_attempt']}**",
            "",
            "## Chi so recognition",
            f"- Accuracy: **{summary['metrics']['accuracy']:.4f}**",
            f"- Top-1 Accuracy: **{summary['top1_metrics']['top1_accuracy']:.4f}**",
            f"- Macro Precision: **{summary['metrics']['macro_precision']:.4f}**",
            f"- Macro Recall: **{summary['metrics']['macro_recall']:.4f}**",
            f"- Macro F1-score: **{summary['metrics']['macro_f1']:.4f}**",
            f"- FAR: **{summary['verification']['false_acceptance_rate']:.4f}**",
            f"- FRR: **{summary['verification']['false_rejection_rate']:.4f}**",
            "",
            "## Danh gia theo muc tieu ky thuat",
            f"- Accuracy > {target_status.get('target_accuracy', TARGET_ACCURACY):.2f}: **{'Dat' if target_status.get('meets_accuracy') else 'Chua dat'}**",
            f"- Top-1 > {target_status.get('target_top1_accuracy', TARGET_TOP1_ACCURACY):.2f}: **{'Dat' if target_status.get('meets_top1_accuracy') else 'Chua dat'}**",
            f"- FAR < {target_status.get('target_far', TARGET_FAR):.2f}: **{'Dat' if target_status.get('meets_far') else 'Chua dat'}**",
            f"- FRR < {target_status.get('target_frr', TARGET_FRR):.2f}: **{'Dat' if target_status.get('meets_frr') else 'Chua dat'}**",
            "",
            "## Operating point de xuat",
            f"- Threshold: **{selected_point.get('threshold', 0.0):.4f}**",
            f"- Accuracy: **{selected_point.get('accuracy', 0.0):.4f}**",
            f"- Top-1 Accuracy: **{selected_point.get('top1_accuracy', 0.0):.4f}**",
            f"- FAR: **{selected_point.get('false_acceptance_rate', 0.0):.4f}**",
            f"- FRR: **{selected_point.get('false_rejection_rate', 0.0):.4f}**",
            f"- Dat toan bo muc tieu: **{'Co' if selected_point.get('meets_all_targets') else 'Khong'}**",
            f"- Accuracy > {selected_target_status.get('target_accuracy', TARGET_ACCURACY):.2f}: **{'Dat' if selected_target_status.get('meets_accuracy') else 'Chua dat'}**",
            f"- Top-1 > {selected_target_status.get('target_top1_accuracy', TARGET_TOP1_ACCURACY):.2f}: **{'Dat' if selected_target_status.get('meets_top1_accuracy') else 'Chua dat'}**",
            f"- FAR < {selected_target_status.get('target_far', TARGET_FAR):.2f}: **{'Dat' if selected_target_status.get('meets_far') else 'Chua dat'}**",
            f"- FRR < {selected_target_status.get('target_frr', TARGET_FRR):.2f}: **{'Dat' if selected_target_status.get('meets_frr') else 'Chua dat'}**",
            "",
            "## Threshold sweep",
            "| Threshold | Accuracy | Top-1 | Macro F1 | FAR | FRR |",
            "| ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
        for item in summary["threshold_sweep"]:
            lines.append(
                f"| {item['threshold']:.2f} | {item['accuracy']:.4f} | {item.get('top1_accuracy', 0.0):.4f} | "
                f"{item['macro_f1']:.4f} | {item['false_acceptance_rate']:.4f} | {item['false_rejection_rate']:.4f} |"
            )
        lines.extend(
            [
                "",
                "## Tep ket qua sinh ra",
                "- `summary.json`: Tong hop chi so recognition",
                "- `cluster_summary.csv`: Thong tin cac cum nguoi gia lap",
                "- `predictions.csv`: Ket qua du doan recognition",
                "- `confusion_matrix.csv`: Ma tran nham lan",
                "- `threshold_sweep.csv`: Bang threshold sweep",
                "",
                "## Luu y",
                "- Ket qua pseudo-label chi phu hop de tham do du lieu.",
                "- Khong nen dung pseudo identity lam bang chung chinh de ket luan do chinh xac recognition trong bao cao.",
            ]
        )
        return "\n".join(lines)

    if summary.get("dataset_type") == "unlabeled_flat_images":
        lines = [
            "# Bao cao kiem tra chat luong dataset khuon mat",
            "",
            "## Cau hinh chay",
            f"- Dataset: `{summary['dataset']}`",
            f"- Tong so anh: **{summary['dataset_overview']['num_images']}**",
            "",
            "## Chi so tong quan",
            f"- Ty le anh trich xuat duoc khuon mat: **{summary['dataset_overview']['face_detection_rate']:.4f}**",
            f"- So anh hop le: **{summary['dataset_overview']['valid_face_images']}**",
            f"- So anh khong hop le: **{summary['dataset_overview']['invalid_images']}**",
            f"- Detector confidence trung binh: **{summary['quality_metrics']['average_detector_confidence']:.4f}**",
            f"- Do sang trung binh: **{summary['quality_metrics']['average_brightness_mean']:.2f}**",
            f"- Do net trung binh (Laplacian variance): **{summary['quality_metrics']['average_blur_variance']:.2f}**",
            f"- Ti le kich thuoc mat trung binh: **{summary['quality_metrics']['average_relative_face_size']:.4f}**",
            "",
            "## Ly do anh bi loai",
            "| Ly do | So luong |",
            "| --- | ---: |",
        ]
        for reason, count in summary["dataset_overview"]["invalid_reason_counts"].items():
            lines.append(f"| {reason} | {count} |")
        lines.extend(
            [
                "",
                "## Tep ket qua sinh ra",
                "- `summary.json`: Tong hop chi so dataset phang",
                "- `image_quality.csv`: Thong tin tung anh va ket qua validate",
                "- `invalid_images.json`: Danh sach anh bi loai va ly do",
                "- `crops/`: Anh mat da cat 160x160 tu cac anh hop le",
            ]
        )
        return "\n".join(lines)

    lines = [
        "# Bao cao danh gia nhan dien khuon mat",
        "",
        "## Cau hinh chay",
        f"- Dataset: `{summary['dataset']}`",
        f"- Tong so lop: **{summary['dataset_overview']['num_classes']}**",
        f"- Tong so anh hop le trong dataset: **{summary['dataset_overview']['num_images']}**",
        f"- Ti le test: **{summary['config']['test_size']}**",
        f"- Nguong chap nhan: **{summary['config']['threshold']}**",
        f"- Margin best match: **{summary['config']['margin']}**",
        f"- Anh dang ky / nguoi: **{summary['config']['gallery_images_per_class']}**",
        f"- Anh diem danh / lan thu: **{summary['config']['checkin_images_per_attempt']}**",
        "",
        "## Chi so tong quan",
        f"- Accuracy: **{summary['metrics']['accuracy']:.4f}**",
        f"- Top-1 Accuracy: **{summary['top1_metrics']['top1_accuracy']:.4f}**",
        f"- Macro Precision: **{summary['metrics']['macro_precision']:.4f}**",
        f"- Macro Recall: **{summary['metrics']['macro_recall']:.4f}**",
        f"- Macro F1-score: **{summary['metrics']['macro_f1']:.4f}**",
        f"- FAR: **{summary['verification']['false_acceptance_rate']:.4f}**",
        f"- FRR: **{summary['verification']['false_rejection_rate']:.4f}**",
        "",
        "## Phan bo du lieu",
        f"- So anh train su dung duoc: **{summary['dataset_overview']['train_valid']}**",
        f"- So anh test: **{summary['dataset_overview']['test_images']}**",
        f"- So lan diem danh mo phong: **{summary['dataset_overview']['checkin_attempts']}**",
        f"- So anh bi loai vi khong phat hien duoc khuon mat: **{summary['dataset_overview']['invalid_images']}**",
        "",
        "## Chi so theo tung lop",
        "| Lop | Precision | Recall | F1-score | Support |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]

    for label, metrics in summary["metrics"]["per_class"].items():
        lines.append(
            f"| {label} | {metrics['precision']:.4f} | {metrics['recall']:.4f} | "
            f"{metrics['f1_score']:.4f} | {metrics['support']} |"
        )

    lines.extend(
        [
            "",
            "## Threshold sweep",
            "| Threshold | Accuracy | Top-1 | Macro F1 | FAR | FRR |",
            "| ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )

    for item in summary["threshold_sweep"]:
        lines.append(
            f"| {item['threshold']:.2f} | {item['accuracy']:.4f} | {summary['top1_metrics']['top1_accuracy']:.4f} | "
            f"{item['macro_f1']:.4f} | {item['false_acceptance_rate']:.4f} | {item['false_rejection_rate']:.4f} |"
        )

    lines.extend(
        [
            "",
            "## Tep ket qua sinh ra",
            "- `summary.json`: Tong hop tat ca chi so",
            "- `predictions.csv`: Ket qua du doan tren tung anh test",
            "- `confusion_matrix.csv`: Ma tran nham lan",
            "- `invalid_images.json`: Danh sach anh khong trich xuat duoc embedding",
            "- `threshold_sweep.csv`: Bang thong ke chi so theo nhieu threshold",
        ]
    )
    return "\n".join(lines)


def main():
    args = parse_args()
    output_dir = Path(args.output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    crop_root_dir = Path(args.crop_output).resolve()

    if args.pseudo_label_datasets:
        aggregate_rows = []
        for dataset in args.pseudo_label_datasets:
            dataset_dir = Path(dataset).resolve()
            if not dataset_dir.exists():
                raise FileNotFoundError(f"Khong tim thay dataset: {dataset_dir}")

            image_paths = collect_flat_images(dataset_dir, args.max_images_per_class)
            if not image_paths:
                raise ValueError(f"Dataset phang khong co anh hop le: {dataset_dir}")

            valid_entries, invalid_images, quality_rows = collect_valid_flat_embeddings(image_paths)
            clusters = cluster_flat_embeddings(
                valid_entries,
                distance_threshold=args.cluster_threshold,
                refine_passes=args.cluster_refine_passes,
            )
            samples, cluster_rows = build_samples_from_clusters(
                clusters,
                min_images=args.cluster_min_images,
                max_images=args.cluster_max_images,
            )
            if not samples:
                raise RuntimeError(
                    f"Khong tao duoc pseudo dataset tu {dataset_dir}. "
                    "Hay giam --cluster-min-images hoac tang --cluster-threshold."
                )

            dataset_output_dir = output_dir / sanitize_name(dataset_dir.name)
            dataset_output_dir.mkdir(parents=True, exist_ok=True)
            summary, predictions, matrix_labels, matrix_rows, invalid_recognition = evaluate_recognition_dataset(
                samples,
                args,
                dataset_dir.name,
                dataset_dir,
            )
            summary["cluster_config"] = {
                "cluster_threshold": args.cluster_threshold,
                "cluster_refine_passes": args.cluster_refine_passes,
                "cluster_min_images": args.cluster_min_images,
                "cluster_max_images": args.cluster_max_images,
                "raw_valid_faces": len(valid_entries),
                "raw_invalid_faces": len(invalid_images),
                "discovered_clusters": len(clusters),
                "eligible_clusters": sum(1 for row in cluster_rows if row["eligible"]),
            }

            write_json(dataset_output_dir / "summary.json", summary)
            write_json(dataset_output_dir / "invalid_images.json", invalid_images + invalid_recognition)
            write_csv(
                dataset_output_dir / "image_quality.csv",
                quality_rows,
                fieldnames=[
                    "path",
                    "valid_face",
                    "reason",
                    "detector_confidence",
                    "brightness_mean",
                    "blur_variance",
                    "relative_face_size",
                    "face_width",
                    "face_height",
                    "processing_time_ms",
                ],
            )
            write_csv(
                dataset_output_dir / "cluster_summary.csv",
                cluster_rows,
                fieldnames=[
                    "cluster_id",
                    "cluster_size",
                    "used_images",
                    "eligible",
                    "avg_intra_distance",
                    "max_intra_distance",
                    "example_path",
                ],
            )
            write_csv(
                dataset_output_dir / "predictions.csv",
                predictions,
                fieldnames=[
                    "attempt_id",
                    "path",
                    "true_label",
                    "predicted_label",
                    "top1_label",
                    "distance",
                    "accepted",
                    "reason",
                    "valid_frames",
                    "total_frames",
                    "margin",
                    "passes_margin",
                ],
            )
            write_csv(
                dataset_output_dir / "confusion_matrix.csv",
                matrix_rows,
                fieldnames=["true_label"] + matrix_labels,
            )
            write_csv(
                dataset_output_dir / "threshold_sweep.csv",
                summary["threshold_sweep"],
                fieldnames=[
                    "threshold",
                    "margin",
                    "accuracy",
                    "top1_accuracy",
                    "macro_precision",
                    "macro_recall",
                    "macro_f1",
                    "false_acceptance_rate",
                    "false_rejection_rate",
                ],
            )
            (dataset_output_dir / "report.md").write_text(build_markdown_report(summary), encoding="utf-8")

            selected_point = summary.get("selected_operating_point") or {}
            aggregate_rows.append(
                {
                    "dataset_name": dataset_dir.name,
                    "dataset_path": str(dataset_dir),
                    "num_raw_images": len(image_paths),
                    "valid_face_images": len(valid_entries),
                    "discovered_clusters": len(clusters),
                    "eligible_clusters": sum(1 for row in cluster_rows if row["eligible"]),
                    "recognition_images": len(samples),
                    "accuracy": summary["metrics"]["accuracy"],
                    "top1_accuracy": summary["top1_metrics"]["top1_accuracy"],
                    "far": summary["verification"]["false_acceptance_rate"],
                    "frr": summary["verification"]["false_rejection_rate"],
                    "selected_threshold": selected_point.get("threshold"),
                    "selected_accuracy": selected_point.get("accuracy"),
                    "selected_top1_accuracy": selected_point.get("top1_accuracy"),
                    "selected_far": selected_point.get("false_acceptance_rate"),
                    "selected_frr": selected_point.get("false_rejection_rate"),
                }
            )

        write_csv(
            output_dir / "pseudo_label_comparison.csv",
            aggregate_rows,
            fieldnames=[
                "dataset_name",
                "dataset_path",
                "num_raw_images",
                "valid_face_images",
                "discovered_clusters",
                "eligible_clusters",
                "recognition_images",
                "accuracy",
                "top1_accuracy",
                "far",
                "frr",
                "selected_threshold",
                "selected_accuracy",
                "selected_top1_accuracy",
                "selected_far",
                "selected_frr",
            ],
        )

        print("Pseudo-label recognition evaluation hoan tat.")
        print(f"Comparison CSV: {output_dir / 'pseudo_label_comparison.csv'}")
        for row in aggregate_rows:
            print(
                f"- {row['dataset_name']}: clusters={row['eligible_clusters']}/{row['discovered_clusters']}, "
                f"recognition_images={row['recognition_images']}, selected_threshold={row['selected_threshold']}, "
                f"accuracy={row['selected_accuracy']:.4f}, FAR={row['selected_far']:.4f}, FRR={row['selected_frr']:.4f}"
            )
        return

    if args.stability_datasets:
        dataset_dirs = []
        for dataset in args.stability_datasets:
            dataset_dir = Path(dataset).resolve()
            if not dataset_dir.exists():
                raise FileNotFoundError(f"Khong tim thay dataset: {dataset_dir}")
            dataset_dirs.append(dataset_dir)

        summaries, comparison_rows = compare_flat_datasets(
            dataset_dirs=dataset_dirs,
            crop_root_dir=crop_root_dir,
            max_images_per_dataset=args.max_images_per_class,
        )

        for item in summaries:
            dataset_slug = sanitize_name(item["summary"]["dataset_name"])
            dataset_output_dir = output_dir / dataset_slug
            dataset_output_dir.mkdir(parents=True, exist_ok=True)
            write_json(dataset_output_dir / "summary.json", item["summary"])
            write_json(dataset_output_dir / "invalid_images.json", item["invalid_images"])
            write_csv(
                dataset_output_dir / "image_quality.csv",
                item["quality_rows"],
                fieldnames=[
                    "path",
                    "valid_face",
                    "reason",
                    "detector_confidence",
                    "brightness_mean",
                    "blur_variance",
                    "relative_face_size",
                    "face_width",
                    "face_height",
                    "processing_time_ms",
                    "crop_saved",
                    "crop_path",
                ],
            )

        comparison_summary = {
            "dataset_type": "flat_dataset_comparison",
            "datasets": [item["summary"] for item in summaries],
            "comparison": comparison_rows,
            "liveness_metrics": build_liveness_metrics(comparison_rows),
            "crop_output_root": str(crop_root_dir),
        }
        write_json(output_dir / "comparison_summary.json", comparison_summary)
        write_csv(
            output_dir / "comparison.csv",
            comparison_rows,
            fieldnames=[
                "dataset_name",
                "dataset_path",
                "num_images",
                "valid_face_images",
                "invalid_images",
                "face_detection_rate",
                "average_detector_confidence",
                "average_brightness_mean",
                "average_blur_variance",
                "average_relative_face_size",
                "average_processing_time_ms",
                "crop_success_rate",
            ],
        )
        (output_dir / "report.md").write_text(build_markdown_report(comparison_summary), encoding="utf-8")

        print("Kiem tra do on dinh backend hoan tat.")
        print(f"Comparison JSON: {output_dir / 'comparison_summary.json'}")
        print(f"Comparison CSV: {output_dir / 'comparison.csv'}")
        print(f"Markdown report: {output_dir / 'report.md'}")
        print(f"Crop root: {crop_root_dir}")
        print("")
        for row in comparison_rows:
            print(
                f"- {row['dataset_name']}: valid={row['valid_face_images']}/{row['num_images']} "
                f"({row['face_detection_rate']:.4f}), crop_success={row['crop_success_rate']:.4f}, "
                f"avg_time_ms={row['average_processing_time_ms']:.2f}"
            )
        return

    if not args.dataset:
        raise ValueError("Can truyen --dataset hoac --stability-datasets.")

    dataset_dir = Path(args.dataset).resolve()

    if not dataset_dir.exists():
        raise FileNotFoundError(f"Khong tim thay dataset: {dataset_dir}")

    samples = collect_samples(dataset_dir, args.max_classes, args.max_images_per_class)
    if not samples:
        flat_images = collect_flat_images(dataset_dir, args.max_images_per_class)
        if not flat_images:
            raise ValueError("Dataset khong co anh hop le.")

        flat_crop_dir = crop_root_dir / sanitize_name(dataset_dir.name)
        flat_summary, quality_rows, invalid_images = analyze_unlabeled_images(flat_images, flat_crop_dir)
        summary = {
            "dataset": str(dataset_dir),
            "config": {
                "mode": "flat_dataset_quality_check",
                "seed": args.seed,
            },
            **flat_summary,
        }

        write_json(output_dir / "summary.json", summary)
        write_json(output_dir / "invalid_images.json", invalid_images)
        write_csv(
            output_dir / "image_quality.csv",
            quality_rows,
            fieldnames=[
                "path",
                "valid_face",
                "reason",
                "detector_confidence",
                "brightness_mean",
                "blur_variance",
                "relative_face_size",
                "face_width",
                "face_height",
                "processing_time_ms",
                "crop_saved",
                "crop_path",
            ],
        )
        (output_dir / "report.md").write_text(build_markdown_report(summary), encoding="utf-8")

        print("Kiem tra dataset phang hoan tat.")
        print(f"Summary JSON: {output_dir / 'summary.json'}")
        print(f"Markdown report: {output_dir / 'report.md'}")
        print(f"Image quality CSV: {output_dir / 'image_quality.csv'}")
        print("")
        print("Chi so tong quan:")
        print(f"- Tong so anh: {summary['dataset_overview']['num_images']}")
        print(f"- Anh hop le: {summary['dataset_overview']['valid_face_images']}")
        print(f"- Anh khong hop le: {summary['dataset_overview']['invalid_images']}")
        print(f"- Ty le phat hien khuon mat: {summary['dataset_overview']['face_detection_rate']:.4f}")
        return

    label_counts = Counter(sample.label for sample in samples)
    train_samples, test_samples = stratified_split(samples, args.test_size, args.seed)

    gallery, invalid_train, gallery_sources = build_attendance_gallery(
        train_samples,
        args.gallery_images_per_class,
    )
    if not gallery:
        raise RuntimeError("Khong tao duoc gallery train. Hay kiem tra dataset va AI model.")

    attempts = build_checkin_attempts(test_samples, args.checkin_images_per_attempt)
    y_true, y_pred, y_top1_pred, invalid_test, predictions = evaluate_attendance_attempts(
        attempts,
        gallery,
        args.threshold,
        args.margin,
    )
    labels = sorted(gallery.keys())

    metrics = classification_metrics(y_true, y_pred, labels)
    top1_metrics = top1_accuracy(y_true, y_top1_pred)
    verification = verification_metrics(predictions, labels, args.threshold)
    sweep = threshold_sweep(predictions, labels, args.threshold_start, args.threshold_end, args.threshold_step, args.margin)
    matrix_labels, matrix_rows = confusion_matrix(y_true, y_pred, labels)
    invalid_images = invalid_train + invalid_test

    summary = {
        "dataset": str(dataset_dir),
        "config": {
            "test_size": args.test_size,
            "threshold": args.threshold,
            "margin": args.margin,
            "seed": args.seed,
            "gallery_images_per_class": args.gallery_images_per_class,
            "checkin_images_per_attempt": args.checkin_images_per_attempt,
        },
        "dataset_overview": {
            "num_classes": len(label_counts),
            "num_images": len(samples),
            "images_per_class": dict(sorted(label_counts.items())),
            "train_images": len(train_samples),
            "train_valid": sum(1 for sample in train_samples if sample.label in gallery),
            "test_images": len(test_samples),
            "checkin_attempts": len(attempts),
            "invalid_images": len(invalid_images),
        },
        "metrics": metrics,
        "top1_metrics": top1_metrics,
        "verification": verification,
        "threshold_sweep": sweep,
        "gallery_classes": labels,
        "gallery_strategy": "average_of_registration_frames_per_person",
        "checkin_strategy": "5_frame_average_embedding_with_best_match_margin",
        "gallery_sources": gallery_sources,
    }

    write_json(output_dir / "summary.json", summary)
    write_json(output_dir / "invalid_images.json", invalid_images)
    write_csv(
        output_dir / "predictions.csv",
        predictions,
        fieldnames=["attempt_id", "path", "true_label", "predicted_label", "top1_label", "distance", "accepted", "reason", "valid_frames", "total_frames", "margin", "passes_margin"],
    )
    write_csv(
        output_dir / "confusion_matrix.csv",
        matrix_rows,
        fieldnames=["true_label"] + matrix_labels,
    )
    write_csv(
        output_dir / "threshold_sweep.csv",
        sweep,
        fieldnames=[
            "threshold",
            "margin",
            "accuracy",
            "macro_precision",
            "macro_recall",
            "macro_f1",
            "false_acceptance_rate",
            "false_rejection_rate",
        ],
    )
    (output_dir / "report.md").write_text(build_markdown_report(summary), encoding="utf-8")

    print("Danh gia hoan tat.")
    print(f"Summary JSON: {output_dir / 'summary.json'}")
    print(f"Markdown report: {output_dir / 'report.md'}")
    print(f"Predictions CSV: {output_dir / 'predictions.csv'}")
    print(f"Confusion matrix CSV: {output_dir / 'confusion_matrix.csv'}")
    print("")
    print("Chi so tong quan:")
    print(f"- Accuracy: {metrics['accuracy']:.4f}")
    print(f"- Top-1 Accuracy: {top1_metrics['top1_accuracy']:.4f}")
    print(f"- Macro Precision: {metrics['macro_precision']:.4f}")
    print(f"- Macro Recall: {metrics['macro_recall']:.4f}")
    print(f"- Macro F1-score: {metrics['macro_f1']:.4f}")
    print(f"- FAR: {verification['false_acceptance_rate']:.4f}")
    print(f"- FRR: {verification['false_rejection_rate']:.4f}")


if __name__ == "__main__":
    main()
