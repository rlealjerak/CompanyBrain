# Acme E-commerce — Support Escalation Paths
**Version:** 2.4  
**Effective Date:** March 15, 2026  
**Owner:** Sandra Mitchell, Head of Operations  

---

## Escalation Tiers

### Tier 1 — Front-Line Support
**Agents:** Emily Rodriguez and any contracted support staff  
**Handles:** Password resets, order status, basic refund eligibility checks (within policy), shipping tracking, account access issues  
**SLA:** 4-hour first response, 24-hour resolution for standard issues  
**Escalate when:** Issue requires a policy exception, order value > $1,000, or customer is flagged as a VIP account

---

### Tier 2 — Senior Support
**Agents:** Marcus Williams (Team Lead) and designated Tier 2 agents  
**Handles:** Refund exceptions, billing disputes up to $2,500, complex shipping claims, complaints escalated from Tier 1  
**SLA:** 2-hour first response, 8-hour resolution  
**Escalate when:** Issue requires billing team involvement, enterprise account flagged, legal threat received, media escalation

---

### Account Management
**Team:** Roberto Leal (Account Manager) and Amy Huang (Customer Success Manager)  
**Handles:** All issues from enterprise accounts (>$100K ARR), contract renewal concerns, pricing disputes for named accounts  
**SLA:** 1-hour response for flagged enterprise accounts, 4-hour for standard named accounts  
**Escalate when:** Contract termination threatened, issue involves pricing exceptions, VIP escalation unresolved after 24 hours

---

### Operations / Management
**Contact:** Sandra Mitchell (Head of Operations), Sarah Chen (VP Customer Success)  
**Handles:** Policy exceptions beyond agent authority, legal threats, media escalation, SLA breach compensation  
**SLA:** 30-minute acknowledgment for critical escalations  

---

## Escalation by Issue Type

| Issue Type | Tier 1 | Tier 2 | Account Mgmt | Operations |
|---|---|---|---|---|
| Standard refund (within 30 days) | ✅ Resolve | — | — | — |
| Refund exception (31–44 days) | Escalate | ✅ Resolve | — | — |
| Refund >44 days | Escalate | Escalate | — | ✅ Resolve |
| Billing dispute <$500 | ✅ Resolve | — | — | — |
| Billing dispute $500–$2,500 | Escalate | ✅ Resolve | — | — |
| Billing dispute >$2,500 | Escalate | Escalate | ✅ Resolve | — |
| Enterprise account complaint | Escalate | Escalate | ✅ Resolve | — |
| Legal threat received | Escalate immediately | Escalate immediately | — | ✅ Resolve |
| VIP unresolved >24h | Escalate | Escalate | Escalate | ✅ Resolve |
| Shipping SLA breach >7 days | ✅ Resolve with compensation | — | — | — |

---

## Critical Escalation Protocol

For any situation involving a legal threat, regulatory inquiry, or media contact:

1. Do **not** make any commitments or statements on behalf of Acme.
2. Immediately notify Sandra Mitchell via phone (not Slack or email).
3. Log the escalation in the ticket with a "legal-hold" tag.
4. Do not close the ticket until Sandra clears it.

---

## On-Call Coverage

Tier 2 provides 24/7 on-call coverage for enterprise accounts. Contact Marcus Williams via PagerDuty for after-hours escalations. Account Management on-call rotates weekly between Roberto Leal and Amy Huang.
