"""Unit tests for the evaluation harness in eval/evaluate.py."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from eval.evaluate import calculate_macro_f1, evaluate_async
from src.schemas.ticket import TicketCategory, TicketPriority, TriageResult


def test_calculate_macro_f1():
    """Test macro F1 calculation across multiple categories."""
    confusion_matrix = {
        "billing": {"billing": 5, "bug": 1},
        "bug": {"bug": 4, "billing": 0},
    }
    categories = ["billing", "bug"]
    f1 = calculate_macro_f1(confusion_matrix, categories)
    assert 0.0 <= f1 <= 1.0
    assert f1 > 0.8


@pytest.mark.asyncio
async def test_evaluate_async_schema_and_output(tmp_path: Path):
    """Test evaluate_async produces the exact submission contract schema."""
    output_file = tmp_path / "test_results.json"

    mock_prediction = TriageResult(
        ticket_id="T-001",
        category=TicketCategory.BILLING,
        priority=TicketPriority.HIGH,
        summary="Refund request for duplicate billing.",
        suggested_reply="We have issued your refund.",
        confidence=0.95,
        escalate=False,
    )

    with patch("eval.evaluate.get_triage_service") as mock_get_service:
        mock_service = AsyncMock()
        mock_service.triage_ticket = AsyncMock(return_value=mock_prediction)
        mock_get_service.return_value = mock_service

        results = await evaluate_async(limit=2, output_path=output_file)

        # 1. Verify returned dictionary structure
        assert "metrics" in results
        assert "predictions" in results
        assert set(results.keys()) == {"metrics", "predictions"}

        # 2. Verify metrics structure
        assert "category_accuracy" in results["metrics"]
        assert "priority_agreement" in results["metrics"]
        assert set(results["metrics"].keys()) == {"category_accuracy", "priority_agreement"}
        assert isinstance(results["metrics"]["category_accuracy"], float)
        assert isinstance(results["metrics"]["priority_agreement"], float)

        # 3. Verify predictions list length
        assert len(results["predictions"]) == 2

        # 4. Verify prediction item schema
        expected_fields = {
            "id",
            "category",
            "priority",
            "summary",
            "suggested_reply",
            "confidence",
            "escalate",
        }
        for pred in results["predictions"]:
            assert set(pred.keys()) == expected_fields
            assert isinstance(pred["id"], str)
            assert isinstance(pred["category"], str)
            assert isinstance(pred["priority"], str)
            assert isinstance(pred["summary"], str)
            assert isinstance(pred["suggested_reply"], str)
            assert isinstance(pred["confidence"], float)
            assert isinstance(pred["escalate"], bool)

        # 5. Verify serialized file on disk
        assert output_file.exists()
        with open(output_file, "r", encoding="utf-8") as f:
            disk_data = json.load(f)
        assert set(disk_data.keys()) == {"metrics", "predictions"}
        assert len(disk_data["predictions"]) == 2
