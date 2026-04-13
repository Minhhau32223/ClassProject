import argparse
import csv
import json
import math
import random
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apps.utils import compare_faces, get_embedding_from_image


VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


@dataclass
class Sample:
    label: str
    path: Path


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Danh gia mo hinh nhan dien khuon mat tren dataset cau truc theo thu muc:"
            " dataset/person_a/*.jpg, dataset/person_b/*.jpg ..."
        )
    )
    parser.add_argument("--dataset", required=True, help="Thu muc dataset goc")
    parser.add_argument("--output", default="reports/face_evaluation", help="Thu muc luu ket qua")
    parser.add_argument("--test-size", type=float, default=0.3, help="Ti le test cho moi lop")
    parser.add_argument("--threshold", type=float, default=0.45, help="Nguong cosine distance de chap nhan")
    parser.add_argument("--seed", type=int, default=42, help="Seed de chia tap train/test")
    parser.add_argument("--max-classes", type=int, default=None, help="Gioi han so nguoi (class) duoc dua vao danh gia")
    parser.add_argument("--max-images-per-class", type=int, default=None, help="Gioi han so anh moi nguoi")
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

    for label, reference_embedding in gallery.items():
        _, distance = compare_faces(embedding, reference_embedding, threshold=threshold)
        if best_distance is None or distance < best_distance:
            best_distance = distance
            best_label = label

    accepted = best_distance is not None and best_distance < threshold
    predicted_label = best_label if accepted else "unknown"
    return predicted_label, best_distance, accepted


def safe_div(numerator, denominator):
    return numerator / denominator if denominator else 0.0


def evaluate(test_samples, gallery, threshold):
    y_true = []
    y_pred = []
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
            predictions.append(
                {
                    "path": str(sample.path),
                    "true_label": sample.label,
                    "predicted_label": "unknown",
                    "distance": None,
                    "accepted": False,
                    "reason": "no_face_detected",
                }
            )
            continue

        predicted_label, distance, accepted = predict_label(embedding, gallery, threshold)
        y_true.append(sample.label)
        y_pred.append(predicted_label)
        predictions.append(
            {
                "path": str(sample.path),
                "true_label": sample.label,
                "predicted_label": predicted_label,
                "distance": float(distance) if distance is not None else None,
                "accepted": accepted,
                "reason": "ok",
            }
        )

    return y_true, y_pred, invalid_images, predictions


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


def verification_metrics(predictions):
    false_reject = 0
    false_accept = 0
    genuine_total = len(predictions)
    impostor_total = len(predictions)

    for prediction in predictions:
        same_identity_rejected = prediction["predicted_label"] != prediction["true_label"]
        if same_identity_rejected:
            false_reject += 1

        different_identity_accepted = (
            prediction["predicted_label"] not in {prediction["true_label"], "unknown"}
        )
        if different_identity_accepted:
            false_accept += 1

    return {
        "false_rejection_rate": safe_div(false_reject, genuine_total),
        "false_acceptance_rate": safe_div(false_accept, impostor_total),
    }


def write_json(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(path: Path, rows, fieldnames):
    with path.open("w", newline="", encoding="utf-8-sig") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_markdown_report(summary):
    lines = [
        "# Bao cao danh gia nhan dien khuon mat",
        "",
        "## Cau hinh chay",
        f"- Dataset: `{summary['dataset']}`",
        f"- Tong so lop: **{summary['dataset_overview']['num_classes']}**",
        f"- Tong so anh hop le trong dataset: **{summary['dataset_overview']['num_images']}**",
        f"- Ti le test: **{summary['config']['test_size']}**",
        f"- Nguong chap nhan: **{summary['config']['threshold']}**",
        "",
        "## Chi so tong quan",
        f"- Accuracy: **{summary['metrics']['accuracy']:.4f}**",
        f"- Macro Precision: **{summary['metrics']['macro_precision']:.4f}**",
        f"- Macro Recall: **{summary['metrics']['macro_recall']:.4f}**",
        f"- Macro F1-score: **{summary['metrics']['macro_f1']:.4f}**",
        f"- FAR: **{summary['verification']['false_acceptance_rate']:.4f}**",
        f"- FRR: **{summary['verification']['false_rejection_rate']:.4f}**",
        "",
        "## Phan bo du lieu",
        f"- So anh train su dung duoc: **{summary['dataset_overview']['train_valid']}**",
        f"- So anh test: **{summary['dataset_overview']['test_images']}**",
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
            "## Tep ket qua sinh ra",
            "- `summary.json`: Tong hop tat ca chi so",
            "- `predictions.csv`: Ket qua du doan tren tung anh test",
            "- `confusion_matrix.csv`: Ma tran nham lan",
            "- `invalid_images.json`: Danh sach anh khong trich xuat duoc embedding",
        ]
    )
    return "\n".join(lines)


def main():
    args = parse_args()
    dataset_dir = Path(args.dataset).resolve()
    output_dir = Path(args.output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    if not dataset_dir.exists():
        raise FileNotFoundError(f"Khong tim thay dataset: {dataset_dir}")

    samples = collect_samples(dataset_dir, args.max_classes, args.max_images_per_class)
    if not samples:
        raise ValueError("Dataset khong co anh hop le.")

    label_counts = Counter(sample.label for sample in samples)
    train_samples, test_samples = stratified_split(samples, args.test_size, args.seed)

    gallery, invalid_train, gallery_sources = build_gallery(train_samples)
    if not gallery:
        raise RuntimeError("Khong tao duoc gallery train. Hay kiem tra dataset va AI model.")

    y_true, y_pred, invalid_test, predictions = evaluate(test_samples, gallery, args.threshold)
    labels = sorted(gallery.keys())

    metrics = classification_metrics(y_true, y_pred, labels)
    verification = verification_metrics(predictions)
    matrix_labels, matrix_rows = confusion_matrix(y_true, y_pred, labels)
    invalid_images = invalid_train + invalid_test

    summary = {
        "dataset": str(dataset_dir),
        "config": {
            "test_size": args.test_size,
            "threshold": args.threshold,
            "seed": args.seed,
        },
        "dataset_overview": {
            "num_classes": len(label_counts),
            "num_images": len(samples),
            "images_per_class": dict(sorted(label_counts.items())),
            "train_images": len(train_samples),
            "train_valid": sum(1 for sample in train_samples if sample.label in gallery),
            "test_images": len(test_samples),
            "invalid_images": len(invalid_images),
        },
        "metrics": metrics,
        "verification": verification,
        "gallery_classes": labels,
        "gallery_strategy": "single_reference_image_per_person",
        "gallery_sources": gallery_sources,
    }

    write_json(output_dir / "summary.json", summary)
    write_json(output_dir / "invalid_images.json", invalid_images)
    write_csv(
        output_dir / "predictions.csv",
        predictions,
        fieldnames=["path", "true_label", "predicted_label", "distance", "accepted", "reason"],
    )
    write_csv(
        output_dir / "confusion_matrix.csv",
        matrix_rows,
        fieldnames=["true_label"] + matrix_labels,
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
    print(f"- Macro Precision: {metrics['macro_precision']:.4f}")
    print(f"- Macro Recall: {metrics['macro_recall']:.4f}")
    print(f"- Macro F1-score: {metrics['macro_f1']:.4f}")
    print(f"- FAR: {verification['false_acceptance_rate']:.4f}")
    print(f"- FRR: {verification['false_rejection_rate']:.4f}")


if __name__ == "__main__":
    main()
