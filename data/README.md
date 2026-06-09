# Acme E-commerce — Synthetic Dataset

This directory contains all synthetic data for the Company Brain demo. The dataset represents a fictional e-commerce company (Acme E-commerce) with realistic internal documents, Slack threads, support tickets, email chains, and structured reference data.

All files are pre-generated and committed so the dataset is fixed and reproducible. To regenerate, run `python scripts/generate_data.py` (requires `ANTHROPIC_API_KEY`).

---

## Directory Structure

```
data/raw/
├── policies/          8 Markdown policy and process documents
├── slack/             6 JSON Slack thread files
├── tickets/           1 JSON file with 30 support tickets
├── emails/            3 JSON email chain files
└── reference/         3 JSON structured reference files
```

---

## Contradiction A — Refund Policy Window (14 days vs. 30 days)

**What it is:** Two policy documents exist simultaneously in the corpus. One says the return window is 14 days; the other says 30 days. A Slack thread provides the authoritative resolution.

| Source | Return Window | Date | Status |
|---|---|---|---|
| `policies/old_refund_policy.md` | **14 days** | December 1, 2025 | Outdated — never marked as superseded |
| `policies/current_refund_policy.md` | **30 days** | April 1, 2026 | **Authoritative current policy** |
| `slack/refund_policy_clarification.json` | Confirms **30 days** | May 8, 2026 | Senior agent explicitly corrects the old policy |

**Expected system behavior:** When a user asks "What is our refund policy?", the RAG pipeline retrieves chunks from both policy documents. The reranking step should surface the April 2026 document above the December 2025 document based on `source_timestamp`. The Claude response should cite both sources, explicitly flag the contradiction, and identify the current_refund_policy.md as authoritative. The Slack confirmation provides a third corroborating signal.

**Why the contradiction persists:** The old policy document was never removed or marked as superseded. Multiple support tickets (TKT-002, TKT-026) show customers and agents being confused by this discrepancy, which is realistic — knowledge base hygiene is a real operational problem.

---

## Contradiction B — Pricing Exception (25% discount vs. 20% manager authority cap)

**What it is:** The pricing policy document explicitly states that Sales Managers can approve a maximum 20% discount. A Slack thread records Sales Manager Jake Torres verbally approving a 25% discount for GlobalTech Solutions. A follow-up email chain shows the billing team flagging this exact discrepancy.

| Source | Claim | Date |
|---|---|---|
| `reference/pricing_table.json` | Sales Manager max discount: **20%** | April 1, 2026 |
| `policies/pricing_rules.md` | Sales Manager max discount: **20%** (verbal approvals not binding) | April 1, 2026 |
| `slack/pricing_exception_approval.json` | Jake Torres approves **25% discount** verbally, instructs team not to create a formal ticket | May 28, 2026 |
| `emails/billing_dispute.json` | Tom Bradley flags the discrepancy; operations resolves via VP sign-off | June 3–4, 2026 |

**Expected system behavior:** A query about discount authority or GlobalTech Solutions should surface both the policy (20% cap) and the Slack exception (25% approved). The system should note the contradiction and flag that the verbal approval required VP-level authorization per policy. The email chain provides the resolution — VP approval was ultimately obtained.

---

## Highest-Priority PIL Task

**Source:** `slack/enterprise_proposal_followup.json`

Sarah Chen (VP Customer Success, Roberto Leal's direct manager) explicitly @mentions Roberto Leal with an urgent request to send the Meridian Technologies enterprise proposal ($250K ARR) by EOD. The request has:
- Explicit @mention of Roberto → +1 urgency bonus
- Sender is Roberto's manager → +1 urgency bonus
- Hard deadline (EOD today) → +2 urgency bonus
- High financial stakes ($250K ARR)

**Expected task:** Description along the lines of "Send updated enterprise pricing proposal to Meridian Technologies (lisa.park@meridiantech.com) by EOD — include $22/seat rate for 120 seats, Net 60 terms, and 4-week onboarding timeline."

**Corroborating email:** `emails/enterprise_account_followup.json` shows the full email exchange, confirming the customer's urgency and the specific terms required.

---

## Additional PIL Tasks

| Source | Task | Priority |
|---|---|---|
| `slack/qbr_planning.json` | Pull TechCorp account history report for Amy Huang by July 8 | Medium |
| `emails/vendor_negotiation.json` | Confirm Cloudware integration timeline in writing by June 12 | High |
| `slack/checkout_bug_discussion.json` | Submit fix PR and update runbook (Priya Patel — implicit) | Medium |

---

## Data Integrity Notes

- All timestamps use ISO 8601 format in UTC
- All ticket IDs follow the format `TKT-NNN`
- All customer IDs follow the format `CUST-NNNN`
- Usernames in Slack threads match the `username` field in `reference/team_directory.json`
- The `thread_ts` fields in Slack files are Unix timestamps and are unique across all files
