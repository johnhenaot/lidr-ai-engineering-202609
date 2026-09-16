"""Static context injected into every prompt (the "cache" in cache-augmented generation).

These are few-shot examples: the model copies their *structure*, so each one
deliberately demonstrates PERT three-point estimation, an explicit contingency
buffer, a range instead of a single number, assumptions, exclusions and risks.

Fictional data, realistic shape. Example 1 is a well-understood project (narrow
range, high confidence); example 2 has an unknown legacy integration (wide
range, low confidence) so the model learns that uncertainty drives the spread.
"""

ESTIMATION_EXAMPLES = [
  {
    "meeting_summary": (
      "The client, an office supplies distributor with 3 warehouses, needs a web "
      "inventory management platform to replace their spreadsheets. They asked for "
      "product create/edit/delete, stock control per warehouse, roles for warehouse "
      "staff and managers, a dashboard with turnover metrics, and a CSV import of "
      "their current catalogue. No mobile app and no accounting integration for now. "
      "Their catalogue is well structured and they have a dedicated project owner."
    ),
    "estimation": """
## Estimate: Inventory Management Platform

### Assumptions
- The client delivers the catalogue as CSV with consistent columns.
- Own email/password authentication (no corporate SSO).
- A single decision-maker, with feedback within 48h.
- Built on an existing component library, no bespoke visual identity.

### Out of scope
- Native mobile application.
- Integration with their accounting software.
- Migration of historical data prior to 2024.
- On-site training (a user manual is included).

### Task breakdown (three-point estimation, hours)
| Task | Optimistic | Likely | Pessimistic | PERT |
|---|---|---|---|---|
| UI/UX design | 28 | 40 | 60 | 41 |
| Backend API (inventory CRUD) | 45 | 60 | 88 | 62 |
| Authentication and roles | 14 | 20 | 32 | 21 |
| Metrics dashboard | 20 | 30 | 50 | 32 |
| Catalogue CSV import | 10 | 16 | 28 | 17 |
| Testing and QA | 18 | 25 | 40 | 26 |
| Deployment and CI/CD | 8 | 12 | 20 | 13 |

**PERT subtotal: 212 hours**
**Contingency (20%): 42 hours**
**Total estimate: 254 hours**
**Likely range: 230-300 hours**

### Recommended team
2 full-stack developers + 1 UX designer (part-time, first 3 weeks)

### Estimated duration
6-8 weeks

### Risks
- **CSV quality (medium):** if the catalogue contains duplicates or inconsistent
  units, the import task can cost twice as much.
- **Metric definitions (low):** the dashboard may grow if new KPIs surface
  during review.

### Confidence
High. Scope is closed and there are no external dependencies. Estimate valid for 30 days.
""",
  },
  {
    "meeting_summary": (
      "The client, a chain of car repair shops with 12 locations, wants an online "
      "booking portal so customers can request appointments. It must show real "
      "availability per location and service, accept a card deposit, and sync with "
      "their current ERP (Navision, on-premise 2016 install) for spare part stock "
      "and customer records. Nobody on the client side knows the ERP API "
      "documentation and the original vendor no longer supports them. They want to "
      "launch before the winter campaign."
    ),
    "estimation": """
## Estimate: Booking Portal with ERP Integration

### Assumptions
- The ERP exposes some integration mechanism (API, web service or intermediate
  database). **This assumption is validated in task 1 and conditions everything else.**
- The client provides an ERP test environment in the first week.
- Payment gateway: Stripe, with the client's account already verified.
- Availability rules are identical across the 12 locations.

### Out of scope
- Any modification inside the ERP itself.
- Migration of the paper-based appointment history.
- Native mobile app (the portal will be responsive).
- Electronic invoicing.

### Task breakdown (three-point estimation, hours)
| Task | Optimistic | Likely | Pessimistic | PERT |
|---|---|---|---|---|
| ERP technical discovery (spike) | 12 | 20 | 40 | 22 |
| Portal UI/UX design | 24 | 36 | 56 | 37 |
| Booking and availability backend | 50 | 72 | 120 | 76 |
| ERP integration (stock and customers) | 40 | 70 | 140 | 77 |
| Stripe payments and refunds | 24 | 36 | 60 | 38 |
| Email/SMS notifications | 10 | 17 | 28 | 18 |
| Testing and QA | 24 | 36 | 60 | 38 |
| Deployment and monitoring | 10 | 16 | 28 | 17 |

**PERT subtotal: 323 hours**
**Contingency (25%): 81 hours**
**Total estimate: 404 hours**
**Likely range: 350-540 hours**

### Recommended team
2 full-stack developers + 1 backend developer experienced in integrations
+ 1 UX designer (part-time)

### Estimated duration
10-13 weeks

### Risks
- **ERP integration (high):** the largest uncertainty in the project. If the ERP
  exposes no viable integration path, this task can triple or require a different
  approach (file-based sync). The pessimistic 140h reflects the worst *known*
  case, not the unknown one.
- **No vendor support (high):** without documentation, discovery can stretch and
  block the rest of the team.
- **Campaign deadline (medium):** the winter target leaves little slack; we
  recommend shipping bookings without the integration as a first release.

### Confidence
Low until the task 1 spike is complete. We recommend contracting only that task
(22h) and re-estimating the rest with real data before fixing a price.
Estimate valid for 15 days.
""",
  },
]
