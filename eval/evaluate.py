"""Empirical evaluation harness for benchmarking all tickets against ground truth labels."""

import argparse
import asyncio
import json
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.core.config import settings
from src.schemas.ticket import Ticket
from src.services.triage import get_triage_service


def calculate_macro_f1(confusion_matrix: Dict[str, Dict[str, int]], categories: List[str]) -> float:
    """Compute Macro F1 score across all evaluated categories."""
    f1_scores = []
    for cat in categories:
        tp = confusion_matrix.get(cat, {}).get(cat, 0)
        fp = sum(confusion_matrix.get(c, {}).get(cat, 0) for c in categories if c != cat)
        fn = sum(confusion_matrix.get(cat, {}).get(c, 0) for c in categories if c != cat)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        if precision + recall > 0:
            f1 = 2 * (precision * recall) / (precision + recall)
        else:
            f1 = 0.0
        f1_scores.append(f1)

    return round(sum(f1_scores) / len(f1_scores), 4) if f1_scores else 0.0


async def evaluate_async(limit: Optional[int] = None) -> Dict[str, Any]:
    """Asynchronously evaluate all 30 tickets and produce submission predictions."""
    base_dir = Path(__file__).resolve().parent.parent
    data_dir = base_dir / "data"
    eval_dir = base_dir / "eval"
    results_path = eval_dir / "results.json"

    tickets_file = data_dir / "tickets.json"
    labels_file = data_dir / "labels.json"

    # 1. Load all tickets from data/tickets.json
    raw_tickets: List[Dict[str, Any]] = []
    if tickets_file.exists():
        with open(tickets_file, "r", encoding="utf-8") as f:
            raw_tickets = json.load(f)

    if limit and limit > 0:
        raw_tickets = raw_tickets[:limit]

    # 2. Load ground-truth labels indexed by ticket id
    labels_by_id: Dict[str, Dict[str, Any]] = {}
    total_labels_count = 0
    if labels_file.exists():
        with open(labels_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            raw_labels = data.get("labels", []) if isinstance(data, dict) else data
            total_labels_count = len(raw_labels)
            for l in raw_labels:
                l_id = l.get("id")
                if l_id:
                    labels_by_id[l_id] = l

    triage_service = get_triage_service()

    total_tickets = len(raw_tickets)
    cat_correct = 0
    priority_correct = 0
    labeled_evaluated_count = 0
    latencies: List[float] = []

    # Confusion matrix structure: true_cat -> {pred_cat: count}
    confusion_matrix: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    predictions: List[Dict[str, Any]] = []
    escalated_count = 0

    print(f"\n🧪 Starting complete evaluation harness: {total_tickets} tickets ({len(labels_by_id)} with ground truth labels)...")
    print(f"   Model: {settings.llm_model} | Endpoint: {settings.llm_base_url}\n")

    for idx, raw_ticket in enumerate(raw_tickets, start=1):
        ticket = Ticket.model_validate(raw_ticket)
        t_id = ticket.id or f"T-{idx:03d}"

        start_time = time.perf_counter()
        try:
            prediction = await triage_service.triage_ticket(ticket)
            latency_ms = (time.perf_counter() - start_time) * 1000
        except Exception as exc:
            latency_ms = (time.perf_counter() - start_time) * 1000
            print(f"❌ Error triaging ticket {t_id}: {exc}")
            # Fallback prediction to maintain schema contract
            prediction = None

        latencies.append(latency_ms)

        if prediction:
            pred_cat = (prediction.category.value if hasattr(prediction.category, "value") else str(prediction.category)).strip().lower()
            pred_pri = (prediction.priority.value if hasattr(prediction.priority, "value") else str(prediction.priority)).strip().lower()
            pred_summary = prediction.summary or ""
            pred_reply = prediction.suggested_reply or ""
            pred_conf = round(float(prediction.confidence), 4) if prediction.confidence is not None else 0.0
            pred_esc = bool(prediction.escalate)
        else:
            pred_cat = "other"
            pred_pri = "medium"
            pred_summary = "Error during triage"
            pred_reply = "We have received your ticket and will follow up shortly."
            pred_conf = 0.0
            pred_esc = True

        if pred_esc:
            escalated_count += 1

        # Strict submission schema for each prediction item
        prediction_item = {
            "id": t_id,
            "category": pred_cat,
            "priority": pred_pri,
            "summary": pred_summary,
            "suggested_reply": pred_reply,
            "confidence": pred_conf,
            "escalate": pred_esc,
        }
        predictions.append(prediction_item)

        # Ground truth comparison if label exists
        label_entry = labels_by_id.get(t_id)
        if label_entry:
            labeled_evaluated_count += 1
            true_cat = label_entry.get("category", "other").strip().lower()
            true_pri = label_entry.get("priority", "medium").strip().lower()

            cat_match = pred_cat == true_cat
            pri_match = pred_pri == true_pri

            if cat_match:
                cat_correct += 1
            if pri_match:
                priority_correct += 1

            confusion_matrix[true_cat][pred_cat] += 1
            mark = "✓" if (cat_match and pri_match) else ("~" if cat_match else "✗")
            label_info = f"| Cat: {pred_cat:<15} (True: {true_cat:<15}) | Pri: {pred_pri:<7} (True: {true_pri:<7})"
        else:
            mark = "•"
            label_info = f"| Cat: {pred_cat:<15} | Pri: {pred_pri:<7}"

        print(f"[{idx:02d}/{total_tickets:02d}] {mark} {t_id:<6} {label_info} | {latency_ms:6.1f}ms")

    # 3. Compute aggregate metrics over labeled subset
    category_acc = round(cat_correct / labeled_evaluated_count, 4) if labeled_evaluated_count > 0 else 0.0
    priority_agree = round(priority_correct / labeled_evaluated_count, 4) if labeled_evaluated_count > 0 else 0.0
    mean_latency = round(sum(latencies) / len(latencies), 2) if latencies else 0.0

    all_categories = sorted(list({c for c in confusion_matrix.keys()} | {c for row in confusion_matrix.values() for c in row.keys()}))
    serializable_confusion = {c: dict(confusion_matrix[c]) for c in confusion_matrix}
    macro_f1 = calculate_macro_f1(confusion_matrix, all_categories)

    results: Dict[str, Any] = {
        "metrics": {
            "category_accuracy": category_acc,
            "priority_agreement": priority_agree,
        },
        "predictions": predictions,
    }

    eval_dir.mkdir(parents=True, exist_ok=True)
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print("🎯 COMPLETE BENCHMARK REPORT SUMMARY")
    print("=" * 60)
    print(f"Total Predictions   : {len(predictions)}/{total_tickets}")
    print(f"Labeled Evaluated   : {labeled_evaluated_count}/{total_labels_count}")
    print(f"Category Accuracy   : {category_acc * 100:.1f}%")
    print(f"Priority Agreement  : {priority_agree * 100:.1f}%")
    print(f"Macro F1 Score      : {macro_f1:.4f}")
    print(f"Mean Latency        : {mean_latency:.1f}ms")
    print(f"Saved Results to    : {results_path}")
    print("=" * 60 + "\n")

    return results


def run_evaluation() -> Dict[str, Any]:
    """Synchronous entry point conforming to Makefile and meta.yaml contract."""
    parser = argparse.ArgumentParser(description="Evaluate Support Inbox Assistant triage model.")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of tickets to evaluate")
    args, _ = parser.parse_known_args()

    return asyncio.run(evaluate_async(limit=args.limit))


if __name__ == "__main__":
    run_evaluation()
