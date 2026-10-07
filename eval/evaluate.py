"""Evaluation harness script for benchmarking ticket triage against ground truth labels."""

import json
from pathlib import Path
from typing import Any, Dict


def run_evaluation() -> Dict[str, Any]:
    """Execute evaluation and return metrics dictionary."""
    base_dir = Path(__file__).resolve().parent.parent
    data_dir = base_dir / "data"
    eval_dir = base_dir / "eval"
    results_path = eval_dir / "results.json"

    tickets_file = data_dir / "tickets.json"
    labels_file = data_dir / "labels.json"

    tickets = []
    labels = []

    if tickets_file.exists():
        try:
            with open(tickets_file, "r", encoding="utf-8") as f:
                tickets = json.load(f)
        except Exception:
            tickets = []

    if labels_file.exists():
        try:
            with open(labels_file, "r", encoding="utf-8") as f:
                raw_labels = json.load(f)
                if isinstance(raw_labels, dict) and "labels" in raw_labels:
                    labels = raw_labels["labels"]
                elif isinstance(raw_labels, list):
                    labels = raw_labels
                else:
                    labels = []
        except Exception:
            labels = []

    # Baseline placeholder metrics structure
    total_tickets = len(tickets) if isinstance(tickets, list) else 0
    results: Dict[str, Any] = {
        "status": "success",
        "total_tickets": total_tickets,
        "total_labels": len(labels) if isinstance(labels, list) else 0,
        "metrics": {
            "accuracy": 0.0,
            "f1_score": 0.0,
            "precision": 0.0,
            "recall": 0.0,
        },
        "details": {
            "evaluated_count": 0,
            "notes": "Initial scaffolding evaluation harness.",
        },
    }

    eval_dir.mkdir(parents=True, exist_ok=True)
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"Evaluation complete. Results saved to {results_path}")
    print(json.dumps(results, indent=2))
    return results


if __name__ == "__main__":
    run_evaluation()
