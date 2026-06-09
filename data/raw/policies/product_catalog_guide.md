# Acme E-commerce — Product Catalog Guide
**Version:** 3.1  
**Effective Date:** May 1, 2026  
**Owner:** Product Team  

---

## SKU Structure

All Acme products use the following SKU format:

```
[CATEGORY]-[PRODUCT_CODE]-[VARIANT]-[REGION]
```

Example: `ELEC-HDMI4K-BLK-US` — Electronics category, HDMI 4K cable, Black variant, US region.

Category codes:
- `ELEC` — Electronics
- `OFFC` — Office supplies
- `HOME` — Home goods
- `SOFT` — Software licenses
- `SERV` — Service subscriptions

---

## Product Lines

### Electronics (ELEC)
Cables, adapters, peripherals, and accessories. High-margin category. Return rate is historically 4.2%, primarily due to compatibility issues. Support agents should verify compatibility before accepting any electronics return as "not as described."

### Office Supplies (OFFC)
Paper, writing instruments, organizational tools. Low SKU complexity, straightforward returns.

### Software Licenses (SOFT)
Digital delivery only. **Non-returnable once activated.** License keys are single-use and cannot be invalidated after delivery. Support has no authority to issue refunds for activated software — escalate any such request to Tier 2 with the Salesforce case attached.

### Service Subscriptions (SERV)
Monthly or annual subscriptions. Cancellations mid-cycle are not refunded but the account remains active until the billing period ends. Annual plan refunds are pro-rated for unused full months only, with a 10% early termination fee.

---

## Bundle Rules

Bundled products (two or more SKUs sold as a package) can only be returned as a complete bundle. Partial bundle returns are not accepted unless the returned item is defective.

Bundle discount: bundles are sold at a 10–20% discount versus individual SKU prices. The discount is displayed on the product page and in the order confirmation.

---

## End-of-Life Procedures

When a product reaches end-of-life (EOL):

1. Product page is updated with "EOL" banner and expected discontinuation date (minimum 60-day notice)
2. Remaining inventory is sold at clearance (20–40% discount, marked as final sale — non-returnable)
3. After inventory is exhausted, SKU is deactivated in the catalog system
4. Support tickets referencing a deactivated SKU should be routed to Tier 2

Current EOL products: check the internal product tracker in Notion for the live list. This document is not updated in real time.

---

## Inventory Thresholds and Alerts

The inventory service triggers alerts at:
- **Yellow alert:** stock falls below 50 units (purchase order review required)
- **Red alert:** stock falls below 20 units (automatic reorder triggers)
- **Out of stock:** order intake halted automatically; existing orders are held for up to 3 business days pending restock confirmation

Engineering maintains the inventory service. For service issues, contact David Kim or create a ticket tagged `#inventory-service`.
