"""Utility script to test the triage model on tickets and record input/output to JSON."""

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.config import settings
from src.schemas.ticket import Ticket
from src.services.triage import get_triage_service


def load_existing_results(file_path: Path) -> List[Dict[str, Any]]:
    """Load existing recorded test results or return empty list."""
    if file_path.exists():
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception:
            return []
    return []


def save_results(file_path: Path, results: List[Dict[str, Any]]) -> None:
    """Save formatted test results to JSON file."""
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)


async def run_test(
    ticket: Ticket,
    output_file: Path = Path("test_results.json"),
) -> Dict[str, Any]:
    """Execute triage on ticket and record input/output."""
    service = get_triage_service()
    
    print(f"\n🚀 Running triage on ticket '{ticket.id or 'manual-test'}': '{ticket.subject}'...")
    result = await service.triage_ticket(ticket)

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": settings.llm_model,
        "parameters": {
            "temperature": settings.llm_temperature,
            "seed": settings.llm_seed,
            "max_tokens": settings.llm_max_tokens,
        },
        "input": {
            "id": ticket.id,
            "channel": ticket.channel,
            "from": ticket.sender,
            "subject": ticket.subject,
            "body": ticket.body,
        },
        "output": {
            "category": result.category.value if result.category else None,
            "priority": result.priority.value if result.priority else None,
            "summary": result.summary,
            "suggested_reply": result.suggested_reply,
            "suggested_tags": result.suggested_tags,
            "confidence": result.confidence,
            "escalate": result.escalate,
        },
    }

    results = load_existing_results(output_file)
    results.append(record)
    save_results(output_file, results)

    print("\n✅ Triage Output:")
    print(f"  • Category:   {record['output']['category']}")
    print(f"  • Priority:   {record['output']['priority']}")
    print(f"  • Confidence: {record['output']['confidence']}")
    print(f"  • Escalate:   {record['output']['escalate']}")
    print(f"  • Summary:    {record['output']['summary']}")
    print(f"  • Reply:      {record['output']['suggested_reply']}")
    print(f"\n📁 Saved result to: {output_file.resolve()} (Total entries: {len(results)})\n")

    return record


def main() -> None:
    parser = argparse.ArgumentParser(description="Test LLM triage model and record input/output.")
    parser.add_argument("--id", default="T-SAMPLE", help="Ticket ID")
    parser.add_argument("--subject", default="Double charged on annual renewal", help="Ticket subject")
    parser.add_argument(
        "--body",
        default="I was charged $199 twice on my card this morning for renewal. Please refund one immediately.",
        help="Ticket body text",
    )
    parser.add_argument("--from-email", dest="sender", default="customer@example.com", help="Sender email")
    parser.add_argument("--channel", default="email", help="Ticket channel (email/chat/webform)")
    parser.add_argument("--output", default="test_results.json", help="Output JSON filename")

    args = parser.parse_args()

    ticket = Ticket(
        id=args.id,
        subject=args.subject,
        body=args.body,
        channel=args.channel,
        sender=args.sender,
    )

    asyncio.run(run_test(ticket, output_file=Path(args.output)))


if __name__ == "__main__":
    main()
