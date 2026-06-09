"""
Synthetic data generator for Acme E-commerce (Company Brain Phase 2).

Two-pass approach:
  Pass 1 — generate clean, realistic internal documents.
  Pass 2 — introduce strategic noise: outdated sections, contradictions,
            and ambiguous references that make the RAG demo interesting.

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    python scripts/generate_data.py

Output is written to data/raw/. The committed files in that directory are
the pre-generated output of this script — re-running will overwrite them.
"""
import json
import os
import sys
from pathlib import Path

import anthropic

ROOT = Path(__file__).parent.parent
DATA_RAW = ROOT / "data" / "raw"
CLIENT = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
MODEL = "claude-opus-4-8"


def generate(prompt: str, system: str = "") -> str:
    kwargs = {"model": MODEL, "max_tokens": 4096, "messages": [{"role": "user", "content": prompt}]}
    if system:
        kwargs["system"] = system
    msg = CLIENT.messages.create(**kwargs)
    return msg.content[0].text


def introduce_noise(content: str, doc_type: str) -> str:
    prompt = f"""
You are editing an internal {doc_type} document for Acme E-commerce.
Introduce realistic noise that would exist in a real company:
- One outdated section that contradicts a newer policy elsewhere
- One ambiguous reference (e.g. "the standard rate" without defining it)
- Natural imperfections in language (fragments, informal phrasing)
Do NOT change names, dates, or ticket IDs. Return only the edited document.

DOCUMENT:
{content}
"""
    return generate(prompt)


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"  wrote {path.relative_to(ROOT)}")


def generate_policies() -> None:
    print("\n[1/5] Generating policy documents...")
    # Policies are pre-committed; this regenerates them if needed.
    # The contradiction (14-day vs 30-day refund window) is intentional.
    specs = [
        ("current_refund_policy.md", "Current refund policy: 30-day window, no-questions-asked for orders under $500. Dated 2026-04-01. Authoritative."),
        ("old_refund_policy.md", "Old refund policy: 14-day window, requires receipt. Dated 2025-12-01. Has NOT been marked as superseded."),
        ("escalation_paths.md", "Escalation matrix: tier 1 support → tier 2 → account manager → VP. By issue type."),
        ("pricing_rules.md", "Standard pricing tiers and max discount authority (15% for sales reps, 20% for managers). Enterprise tier: $24/seat/month."),
        ("shipping_policy.md", "Shipping SLAs, carrier partners, international restrictions."),
        ("vip_customer_handling.md", "VIP account criteria (>$100K ARR), white-glove support procedures."),
        ("new_customer_onboarding.md", "30-day onboarding checklist: kickoff call, integration support, training sessions."),
        ("product_catalog_guide.md", "Product lines, SKU structure, bundle rules, end-of-life procedures."),
    ]
    for filename, spec in specs:
        prompt = f"Write a realistic internal Acme E-commerce policy document. Spec: {spec}. Use markdown. 400-600 words."
        content = generate(prompt)
        content = introduce_noise(content, "policy")
        write(DATA_RAW / "policies" / filename, content)


def generate_slack_threads() -> None:
    print("\n[2/5] Generating Slack threads...")
    threads = [
        ("refund_policy_clarification.json", "Support thread: agent asks about refund window, senior agent Marcus Williams confirms it is now 30 days per the April 2026 update."),
        ("enterprise_proposal_followup.json", "Manager Sarah Chen urgently @mentions Roberto Leal: the Meridian Technologies enterprise proposal ($250K ARR) is overdue, procurement is waiting, send updated pricing by EOD with Net 60 terms."),
        ("checkout_bug_discussion.json", "Engineering thread: David Kim reports 3% checkout 500-error rate in electronics category, Priya Patel investigates timeout in inventory service, implicit action items for a fix PR and runbook update."),
        ("pricing_exception_approval.json", "Sales thread: Jake Torres verbally approves 25% discount for GlobalTech Solutions ($18/seat instead of $24), tells team not to create a formal ticket — contradiction with pricing doc's 20% manager cap."),
        ("qbr_planning.json", "Customer success thread: Amy Huang plans Q3 QBR for TechCorp on July 15, asks Roberto Leal for account history report by July 8."),
        ("product_feedback_sync.json", "Product sync: team discussing feature requests from enterprise customers, soft deadlines for roadmap items."),
    ]
    for filename, spec in threads:
        prompt = f"""Generate a realistic Slack thread JSON for Acme E-commerce.
Spec: {spec}
Schema: {{"thread_ts": "unix_ts_string", "channel": "#channel", "topic": "string", "messages": [{{"ts": "string", "user": "username", "display_name": "Full Name", "text": "message", "is_reply": bool}}]}}
Return only valid JSON, no markdown fences."""
        content = generate(prompt)
        write(DATA_RAW / "slack" / filename, content)


def generate_tickets() -> None:
    print("\n[3/5] Generating support tickets...")
    prompt = """Generate 30 realistic Acme E-commerce support tickets as a JSON array.
Include a mix of: refund requests (some citing the old 14-day policy), shipping complaints, billing disputes, technical issues.
Schema per ticket: {"ticket_id":"TKT-NNN","customer_id":"CUST-NNNN","customer_name":"string","subject":"string","body":"string","status":"open|in_progress|resolved|closed","priority":"low|medium|high|urgent","category":"refund|shipping|billing|technical","created_at":"ISO8601","resolved_at":"ISO8601|null","resolution_notes":"string|null"}
Return only valid JSON array, no markdown fences."""
    content = generate(prompt)
    write(DATA_RAW / "tickets" / "support_tickets.json", content)


def generate_emails() -> None:
    print("\n[4/5] Generating email chains...")
    chains = [
        ("enterprise_account_followup.json", "Account manager Roberto Leal exchanges emails with Lisa Park at Meridian Technologies about their enterprise contract renewal. Action item: Roberto must send updated SLA terms by Friday."),
        ("billing_dispute.json", "Internal email chain between billing specialist Tom Bradley and sales manager Jake Torres about a disputed invoice that references pricing terms inconsistent with the pricing document."),
        ("vendor_negotiation.json", "Vendor negotiation chain with Cloudware Inc. Action item buried in message 4: Roberto Leal needs to confirm the integration timeline before the vendor will proceed."),
    ]
    for filename, spec in chains:
        prompt = f"""Generate a realistic email chain JSON for Acme E-commerce.
Spec: {spec}
Schema: {{"message_id":"string","subject":"string","messages":[{{"from":"Name <email>","to":["Name <email>"],"date":"ISO8601","body":"string"}}]}}
Return only valid JSON, no markdown fences."""
        content = generate(prompt)
        write(DATA_RAW / "emails" / filename, content)


def generate_reference() -> None:
    print("\n[5/5] Generating reference data...")
    pricing_prompt = """Generate Acme E-commerce pricing table JSON.
Include: Starter ($8/seat/month, up to 10 seats), Growth ($16/seat/month, up to 50 seats), Enterprise ($24/seat/month, unlimited seats).
Include discount rules: sales reps can approve up to 15%, managers up to 20%. Annual commitment gives 10% additional.
Schema: {"last_updated":"2026-04-01","tiers":[...],"discount_rules":{...},"coupon_codes":[...]}
Return only valid JSON."""
    write(DATA_RAW / "reference" / "pricing_table.json", generate(pricing_prompt))

    escalation_prompt = """Generate Acme E-commerce escalation matrix JSON.
Map issue types (billing, technical, shipping, refund, VIP) and severity (low/medium/high/critical) to: first_responder, escalation_path, sla_hours, on_call_required.
Schema: {"last_updated":"2026-03-15","rules":[{"issue_type":"string","severity":"string","first_responder":"username","escalation_path":["username"],"sla_hours":int,"on_call_required":bool}]}
Return only valid JSON."""
    write(DATA_RAW / "reference" / "escalation_matrix.json", generate(escalation_prompt))

    team_prompt = """Generate Acme E-commerce team directory JSON with these employees:
- Sarah Chen, VP Customer Success, manages Roberto Leal and Amy Huang
- Roberto Leal, Account Manager, reports to Sarah Chen
- Amy Huang, Customer Success Manager, reports to Sarah Chen
- Marcus Williams, Senior Support Agent (team lead), reports to Sandra Mitchell
- Emily Rodriguez, Support Agent, reports to Marcus Williams
- David Kim, Engineering Lead, manages Priya Patel
- Priya Patel, Software Engineer, reports to David Kim
- Jake Torres, Sales Manager, manages Lisa Nakamura
- Lisa Nakamura, Sales Representative, reports to Jake Torres
- Tom Bradley, Billing Specialist, reports to Sandra Mitchell
- Sandra Mitchell, Head of Operations

Schema: {"company":"Acme E-commerce","last_updated":"2026-06-01","employees":[{"name":"string","username":"string","email":"string","role":"string","department":"string","manager_username":"string|null","is_manager":bool}]}
Return only valid JSON."""
    write(DATA_RAW / "reference" / "team_directory.json", generate(team_prompt))


if __name__ == "__main__":
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY is not set.", file=sys.stderr)
        sys.exit(1)
    generate_policies()
    generate_slack_threads()
    generate_tickets()
    generate_emails()
    generate_reference()
    print("\nDone. All files written to data/raw/")
