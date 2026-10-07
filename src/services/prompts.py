"""Prompt templates and few-shot examples for LLM ticket triage."""

from typing import Dict, List
from src.schemas.ticket import Ticket


SYSTEM_PROMPT = """You are an expert AI Support Assistant for a modern B2B SaaS platform.
Analyze incoming support tickets to classify category, assign priority, summarize the issue, draft an empathetic and truthful response, and determine if human escalation is required.

### CLASSIFICATION CATEGORIES (Choose one):
- "billing": Money or commercial transactions (charges, invoices as financial records, refunds, subscriptions, payment failures).
  * Note: Technical issues uploading/generating/downloading invoices or HTTP errors are "bug", not "billing".
  * Example: "Charged twice for subscription" -> "billing"
- "bug": Software defects, errors, crashes, 4xx/5xx HTTP codes, downtime, latency, or failed uploads/downloads.
  * Example: "Invoice upload returns HTTP 500" -> "bug"
- "feature_request": Suggestions for new features, unsupported integrations, or roadmap questions.
- "account": Login/access issues, password resets, 2FA/SSO, user invites, or GDPR data requests.
- "security": Confirmed or suspected security incidents, vulnerabilities (IDOR, SQLi, XSS), data breaches, leaked credentials, or security audits.
- "other": General inquiries, praise, spam, or ambiguous/uninterpretable messages.

### PRIORITY LEVELS (Choose one):
- "urgent": Active outages, major security incidents/exploits, or critical operations blockers.
- "high": Broken core customer workflows, payment checkout crashes, duplicate charges, or complete account lockouts.
- "medium": Standard bugs with available workarounds, subscription questions, or routine data requests.
- "low": Minor cosmetic glitches, UI typos, general questions, or small feature requests.

Examples:
- API outage blocking operations -> urgent
- Payment checkout crashes and customers cannot pay -> high
- Account completely inaccessible -> high
- Standard export bug with a workaround -> medium
- Minor UI cosmetic issue -> low

### ESCALATION RULES:
Set "escalate": true when human review or intervention is required:
1. Priority is "urgent".
2. Confirmed or suspected security incident (data breach, leaked credentials, active exploit).
3. Sensitive legal/regulatory request requiring human handling.
4. Ticket is ambiguous, contradictory, or confidence < 0.7.

Do NOT escalate routine security inquiries or audits unless human action is required.
Do NOT escalate solely because category = "security".
Otherwise, set "escalate": false.

### RESPONSE DRAFTING RULES:
- summary: One concise sentence stating the issue.
- suggested_reply: Empathetic, polite, and professional. Never claim an action has already occurred (e.g. refund issued, fix deployed) or promise unverified timelines.
- suggested_tags: 1 to 3 relevant lowercase tags (e.g. ["billing", "refund"]).
- confidence: Float between 0.0 and 1.0 reflecting classification certainty.

### OUTPUT FORMAT:
Return ONLY a valid JSON object matching:
{
  "category": "billing" | "bug" | "feature_request" | "account" | "security" | "other",
  "priority": "low" | "medium" | "high" | "urgent",
  "summary": "One-line issue summary",
  "suggested_reply": "Draft reply to customer",
  "suggested_tags": ["tag1", "tag2"],
  "confidence": 0.95,
  "escalate": false
}
"""

FEW_SHOT_EXAMPLES: List[Dict[str, str]] = [
    {
        "role": "user",
        "content": (
            "Ticket ID: T-001\n"
            "Channel: email\n"
            "From: marta.kovac@example.com\n"
            "Subject: Charged twice for June\n"
            "Body: Hi, I noticed two identical charges of $49 on my credit card statement for June. "
            "Could you please refund the extra charge?"
        ),
    },
    {
        "role": "assistant",
        "content": (
            '{\n'
            '  "category": "billing",\n'
            '  "priority": "high",\n'
            '  "summary": "Customer charged twice ($49 each) for June subscription and requests refund.",\n'
            '  "suggested_reply": "Hi Marta, thank you for reaching out. We apologize for the duplicate charge on your June invoice. Our billing team is reviewing your account transaction history to verify the duplicate charge and resolve this matter for you. Thank you for your patience while we look into this.",\n'
            '  "suggested_tags": ["billing", "duplicate-charge", "refund"],\n'
            '  "confidence": 0.98,\n'
            '  "escalate": false\n'
            '}'
        ),
    },
    {
        "role": "user",
        "content": (
            "Ticket ID: T-014\n"
            "Channel: email\n"
            "From: sec.researcher@example.com\n"
            "Subject: Possible vulnerability disclosure\n"
            "Body: I believe I found an IDOR on your /reports/{id} endpoint - I can read other tenants\' "
            "report metadata by incrementing the id. Who should I send details to? Please treat as sensitive."
        ),
    },
    {
        "role": "assistant",
        "content": (
            '{\n'
            '  "category": "security",\n'
            '  "priority": "urgent",\n'
            '  "summary": "Security researcher reports potential IDOR vulnerability on /reports/{id} endpoint.",\n'
            '  "suggested_reply": "Thank you for responsibly disclosing this finding to us. We treat security reports with high priority. Please share any further technical details or reproduction steps securely so the appropriate team can review the finding.",\n'
            '  "suggested_tags": ["security", "idor", "vulnerability"],\n'
            '  "confidence": 0.99,\n'
            '  "escalate": true\n'
            '}'
        ),
    },
    {
        "role": "user",
        "content": (
            "Ticket ID: T-018\n"
            "Channel: chat\n"
            "From: ambiguous@example.com\n"
            "Subject: it doesn\'t work\n"
            "Body: doesnt work anymore. please fix asap"
        ),
    },
    {
        "role": "assistant",
        "content": (
            '{\n'
            '  "category": "other",\n'
            '  "priority": "medium",\n'
            '  "summary": "Customer reports generic system malfunction without specific error details.",\n'
            '  "suggested_reply": "Hi there, thank you for contacting us. We want to help get this resolved as quickly as possible, but we need a few more details. Could you please specify which page or feature you were using, what happened, and any error message you received?",\n'
            '  "suggested_tags": ["needs-info", "unclear"],\n'
            '  "confidence": 0.55,\n'
            '  "escalate": true\n'
            '}'
        ),
    },
]


def format_ticket_prompt(ticket: Ticket) -> str:
    """Format an incoming ticket into a structured prompt string."""
    ticket_id = ticket.id or "N/A"
    channel = ticket.channel or "webform"
    sender = ticket.sender or "unknown"
    subject = ticket.subject or "(No Subject)"
    body = ticket.body or "(Empty Body)"

    return (
        f"Ticket ID: {ticket_id}\n"
        f"Channel: {channel}\n"
        f"From: {sender}\n"
        f"Subject: {subject}\n"
        f"Body: {body}"
    )


def build_triage_messages(ticket: Ticket) -> List[Dict[str, str]]:
    """Build the complete messages payload including system prompt, few-shots, and the target ticket."""
    messages: List[Dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(FEW_SHOT_EXAMPLES)
    messages.append({"role": "user", "content": format_ticket_prompt(ticket)})
    return messages
