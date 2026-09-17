from app.domain.estimate import (
    Duration,
    EstimateDraft,
    HourlyRate,
    Risk,
    TaskDraft,
    TeamMember,
)

_EX1_DRAFT = EstimateDraft(
    meeting_summary=(
        "The client, an office supplies distributor with 3 warehouses, "
        "needs a web inventory management platform to replace their "
        "spreadsheets. They asked for product create/edit/delete, stock "
        "control per warehouse, roles for warehouse staff and managers, "
        "a dashboard with turnover metrics, and a CSV import of their "
        "current catalogue. No mobile app and no accounting integration "
        "for now. Their catalogue is well structured and they have a "
        "dedicated project owner. The agreed billing rate is 100 EUR/hour."
    ),
    estimate_title="Inventory Management Platform",
    assumptions=[
        "The client delivers the catalogue as CSV with consistent columns.",
        "Own email/password authentication (no corporate SSO).",
        "A single decision-maker, with feedback within 48h.",
        "Built on an existing component library, no bespoke visual identity.",
    ],
    out_of_scope=[
        "Native mobile application.",
        "Integration with their accounting software.",
        "Migration of historical data prior to 2024.",
        "On-site training and end-user documentation.",
    ],
    tasks=[
        TaskDraft(
            name="UI/UX design",
            optimistic=28,
            likely=40,
            pessimistic=60,
        ),
        TaskDraft(
            name="Backend API (inventory CRUD)",
            optimistic=45,
            likely=60,
            pessimistic=88,
        ),
        TaskDraft(
            name="Authentication and roles",
            optimistic=14,
            likely=20,
            pessimistic=32,
        ),
        TaskDraft(
            name="Metrics dashboard",
            optimistic=20,
            likely=30,
            pessimistic=50,
        ),
        TaskDraft(
            name="Catalogue CSV import",
            optimistic=10,
            likely=16,
            pessimistic=28,
        ),
        TaskDraft(
            name="Testing and QA",
            optimistic=18,
            likely=25,
            pessimistic=40,
        ),
        TaskDraft(
            name="Deployment and CI/CD",
            optimistic=8,
            likely=12,
            pessimistic=20,
        ),
    ],
    team=[
        TeamMember(role="full-stack developers", quantity=2, details=""),
        TeamMember(
            role="UX designer",
            quantity=1,
            details="part-time, first 3 weeks",
        ),
    ],
    duration=Duration(floor=6, ceiling=8, unit="weeks"),
    risks=[
        Risk(
            label="CSV quality",
            impact="medium",
            detail=(
                "if the catalogue contains duplicates or inconsistent "
                "units, the import task can cost twice as much."
            ),
        ),
        Risk(
            label="Metric definitions",
            impact="low",
            detail="the dashboard may grow if new KPIs surface during review.",
        ),
    ],
    confidence="High",
    confidence_rationale=("Scope is closed and there are no external dependencies."),
    validity_days=30,
    rate=HourlyRate(amount=100.0, currency="EUR"),
)

_EX2_DRAFT = EstimateDraft(
    meeting_summary=(
        "The client, a chain of car repair shops with 12 locations, "
        "wants an online booking portal so customers can request "
        "appointments. It must show real availability per location and "
        "service, accept a card deposit, and sync with their current ERP "
        "(Navision, on-premise 2016 install) for spare part stock and "
        "customer records. Nobody on the client side knows the ERP API "
        "documentation and the original vendor no longer supports them. "
        "They want to launch before the winter campaign (November, "
        "~14 weeks away)."
    ),
    estimate_title="Booking Portal with ERP Integration",
    assumptions=[
        (
            "The ERP exposes some integration mechanism (API, web "
            "service or intermediate database). This assumption is "
            "validated in task 1 and conditions everything else."
        ),
        "The client provides an ERP test environment in the first week.",
        ("Payment gateway: Stripe, with the client's account already verified."),
        "Availability rules are identical across the 12 locations.",
    ],
    out_of_scope=[
        "Any modification inside the ERP itself.",
        "Migration of the paper-based appointment history.",
        "Native mobile app (the portal will be responsive).",
        "Electronic invoicing.",
    ],
    tasks=[
        TaskDraft(
            name="ERP technical discovery (spike)",
            optimistic=12,
            likely=20,
            pessimistic=40,
        ),
        TaskDraft(
            name="Portal UI/UX design",
            optimistic=24,
            likely=36,
            pessimistic=56,
        ),
        TaskDraft(
            name="Booking and availability backend",
            optimistic=50,
            likely=72,
            pessimistic=120,
        ),
        TaskDraft(
            name="ERP integration (stock and customers)",
            optimistic=40,
            likely=70,
            pessimistic=140,
        ),
        TaskDraft(
            name="Stripe payments and refunds",
            optimistic=24,
            likely=36,
            pessimistic=60,
        ),
        TaskDraft(
            name="Email/SMS notifications",
            optimistic=10,
            likely=17,
            pessimistic=28,
        ),
        TaskDraft(
            name="Testing and QA",
            optimistic=24,
            likely=36,
            pessimistic=60,
        ),
        TaskDraft(
            name="Deployment and monitoring",
            optimistic=10,
            likely=16,
            pessimistic=28,
        ),
    ],
    team=[
        TeamMember(role="full-stack developers", quantity=2, details=""),
        TeamMember(
            role="backend developer",
            quantity=1,
            details="experienced in integrations",
        ),
        TeamMember(role="UX designer", quantity=1, details="part-time"),
    ],
    duration=Duration(floor=10, ceiling=13, unit="weeks"),
    risks=[
        Risk(
            label="ERP integration",
            impact="high",
            detail=(
                "the largest uncertainty in the project. If the ERP "
                "exposes no viable integration path, this task can "
                "triple or require a different approach (file-based "
                "sync). The pessimistic 140h reflects the worst known "
                "case, not the unknown one."
            ),
        ),
        Risk(
            label="No vendor support",
            impact="high",
            detail=(
                "without documentation, discovery can stretch and "
                "block the rest of the team."
            ),
        ),
        Risk(
            label="Campaign deadline",
            impact="medium",
            detail=(
                "the winter target leaves little slack; we recommend "
                "shipping bookings without the integration as a first "
                "release."
            ),
        ),
    ],
    confidence="Low",
    confidence_rationale=(
        "The task 1 spike must complete before the rest can be "
        "priced; we recommend contracting only that task and "
        "re-estimating with real data before fixing a price."
    ),
    validity_days=15,
)

ESTIMATION_EXAMPLES: list[EstimateDraft] = [_EX1_DRAFT, _EX2_DRAFT]
