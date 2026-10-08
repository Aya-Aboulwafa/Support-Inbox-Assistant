"""Empirical evaluation harness for benchmarking ticket triage against ground truth labels."""

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
    """Asynchronously evaluate tickets against ground truth labels."""
    base_dir = Path(__file__).resolve().parent.parent
    data_dir = base_dir / "data"
    eval_dir = base_dir / "eval"
    results_path = eval_dir / "results.json"

    tickets_file = data_dir / "tickets.json"
    labels_file = data_dir / "labels.json"

    # 1. Load tickets and labels
    tickets_by_id = {}
    if tickets_file.exists():
        with open(tickets_file, "r", encoding="utf-8") as f:
            for item in json.load(f):
                t_id = item.get("id")
                if t_id:
                    tickets_by_id[t_id] = item

    labels = []
    if labels_file.exists():
        with open(labels_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            labels = data.get("labels", []) if isinstance(data, dict) else data

    if limit and limit > 0:
        labels = labels[:limit]

    triage_service = get_triage_service()

    total_labeled = len(labels)
    cat_correct = 0
    priority_correct = 0
    latencies: List[float] = []

    # Confusion matrix structure: true_cat -> {pred_cat: count}
    confusion_matrix: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    ticket_evaluations: List[Dict[str, Any]] = []

    # Escalation tracking
    escalated_count = 0

    print(f"\n🧪 Starting evaluation harness: {total_labeled} labeled tickets...")
    print(f"   Model: {settings.llm_model} | Endpoint: {settings.llm_base_url}\n")

    for idx, label_entry in enumerate(labels, start=1):
        t_id = label_entry["id"]
        true_cat = label_entry.get("category", "other").strip().lower()
        true_pri = label_entry.get("priority", "medium").strip().lower()

        raw_ticket = tickets_by_id.get(t_id)
        if not raw_ticket:
            print(f"⚠️ Ticket {t_id} not found in tickets.json, skipping...")
            continue

        ticket = Ticket.model_validate(raw_ticket)

        start_time = time.perf_counter()
        try:
            prediction = await triage_service.triage_ticket(ticket)
            latency_ms = (time.perf_counter() - start_time) * 1000
        except Exception as exc:
            latency_ms = (time.perf_counter() - start_time) * 1000
            print(f"❌ Error triaging ticket {t_id}: {exc}")
            continue

        latencies.append(latency_ms)

        pred_cat = (prediction.category.value if hasattr(prediction.category, "value") else str(prediction.category)).strip().lower()
        pred_pri = (prediction.priority.value if hasattr(prediction.priority, "value") else str(prediction.priority)).strip().lower()

        cat_match = pred_cat == true_cat
        pri_match = pred_pri == true_pri

        if cat_match:
            cat_correct += 1
        if pri_match:
            priority_correct += 1
        if prediction.escalate:
            escalated_count += 1

        confusion_matrix[true_cat][pred_cat] += 1

        mark = "✓" if (cat_match and pri_match) else ("~" if cat_match else "✗")
        print(
            f"[{idx:02d}/{total_labeled:02d}] {mark} {t_id} | "
            f"Cat: {pred_cat:<15} (True: {true_cat:<15}) | "
            f"Pri: {pred_pri:<7} (True: {true_pri:<7}) | "
            f"{latency_ms:6.1f}ms"
        )

        ticket_evaluations.append({
            "id": t_id,
            "category": {"predicted": pred_cat, "ground_truth": true_cat, "match": cat_match},
            "priority": {"predicted": pred_pri, "ground_truth": true_pri, "match": pri_match},
            "confidence": prediction.confidence,
            "escalate": prediction.escalate,
            "latency_ms": round(latency_ms, 2),
        })

    # 2. Compute aggregate metrics
    evaluated_count = len(ticket_evaluations)
    category_acc = round(cat_correct / evaluated_count, 4) if evaluated_count > 0 else 0.0
    priority_agree = round(priority_correct / evaluated_count, 4) if evaluated_count > 0 else 0.0
    mean_latency = round(sum(latencies) / len(latencies), 2) if latencies else 0.0

    all_categories = sorted(list({c for c in confusion_matrix.keys()} | {c for row in confusion_matrix.values() for c in row.keys()}))
    serializable_confusion = {c: dict(confusion_matrix[c]) for c in confusion_matrix}
    macro_f1 = calculate_macro_f1(confusion_matrix, all_categories)

    results: Dict[str, Any] = {
        "status": "success",
        "total_tickets": len(tickets_by_id),
        "total_labels": total_labeled,
        "metrics": {
            "category_accuracy": category_acc,
            "priority_agreement": priority_agree,
            "macro_f1": macro_f1,
            "escalation_count": escalated_count,
            "mean_latency_ms": mean_latency,
        },
        "confusion_matrix": serializable_confusion,
        "details": {
            "evaluated_count": evaluated_count,
            "model": settings.llm_model,
            "temperature": settings.llm_temperature,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        "evaluations": ticket_evaluations,
    }

    eval_dir.mkdir(parents=True, exist_ok=True)
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print("🎯 EVALUATION REPORT SUMMARY")
    print("=" * 60)
    print(f"Evaluated Tickets   : {evaluated_count}/{total_labeled}")
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
