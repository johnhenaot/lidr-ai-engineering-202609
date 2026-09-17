from app.domain.estimate import (
    Duration,
    EstimateDraft,
    HourlyRate,
    TeamMember,
)

_CONTINGENCY_RATES = {
    "High": 20,
    "Medium": 23,
    "Low": 25,
}


def _calculate_pert(optimistic: int, likely: int, pessimistic: int) -> int:
    return (optimistic + 4 * likely + pessimistic + 3) // 6


def _calculate_contingency(subtotal: int, confidence: str) -> tuple[int, int]:
    rate = _CONTINGENCY_RATES[confidence]
    amount = (subtotal * rate + 50) // 100
    return rate, amount


def _format_team(members: list[TeamMember]) -> str:
    formatted_members = []
    for member in members:
        if member.details:
            formatted_members.append(
                f"{member.quantity} {member.role} ({member.details})"
            )
        else:
            formatted_members.append(f"{member.quantity} {member.role}")
    return " + ".join(formatted_members)


def _format_duration(duration: Duration) -> str:
    if duration.floor == duration.ceiling:
        return f"{duration.floor} {duration.unit}"
    return f"{duration.floor}-{duration.ceiling} {duration.unit}"


def _format_budget(
    total_hours: int,
    pert_subtotal: int,
    pessimistic_sum: int,
    rate: HourlyRate,
) -> str:
    cents_rate = round(rate.amount * 100)
    total_cents = total_hours * cents_rate
    subtotal_cents = pert_subtotal * cents_rate
    pessimistic_cents = pessimistic_sum * cents_rate

    rate_str = f"{rate.amount:,.2f} {rate.currency}/hour"
    total_str = f"{total_cents / 100:,.2f} {rate.currency}"
    range_str = (
        f"{subtotal_cents / 100:,.2f}-{pessimistic_cents / 100:,.2f} {rate.currency}"
    )

    return (
        f"\n\n### Budget ({rate_str})\n"
        f"**Total: {total_str}**  \n"
        f"**Likely range: {range_str}**"
    )


def render_markdown(draft: EstimateDraft) -> str:
    assumptions_block = "\n".join(f"- {a}" for a in draft.assumptions)
    out_of_scope_block = "\n".join(f"- {o}" for o in draft.out_of_scope)

    task_rows = []
    pert_subtotal = 0
    pessimistic_sum = 0
    for task in draft.tasks:
        pert = _calculate_pert(task.optimistic, task.likely, task.pessimistic)
        pert_subtotal += pert
        pessimistic_sum += task.pessimistic
        task_rows.append(
            f"| {task.name} | {task.optimistic} | {task.likely} | "
            f"{task.pessimistic} | {pert} |"
        )

    table_content = "\n".join(task_rows)
    contingency_rate, contingency_amount = _calculate_contingency(
        pert_subtotal, draft.confidence
    )
    total_estimate = pert_subtotal + contingency_amount

    budget_block = ""
    if draft.rate is not None:
        budget_block = _format_budget(
            total_estimate, pert_subtotal, pessimistic_sum, draft.rate
        )

    team_line = _format_team(draft.team)
    duration_line = _format_duration(draft.duration)
    risks_block = "\n".join(
        f"- **{r.label} ({r.impact}):** {r.detail}" for r in draft.risks
    )

    return (
        f"## Estimate: {draft.estimate_title}\n\n"
        f"### Assumptions\n"
        f"{assumptions_block}\n\n"
        f"### Out of scope\n"
        f"{out_of_scope_block}\n\n"
        f"### Task breakdown (three-point estimation, hours)\n"
        f"| Task | Optimistic | Likely | Pessimistic | PERT |\n"
        f"|---|---|---|---|---|\n"
        f"{table_content}\n\n"
        f"**PERT subtotal: {pert_subtotal} hours**  \n"
        f"**Contingency ({contingency_rate}%): {contingency_amount} hours**  \n"
        f"**Total estimate: {total_estimate} hours**  \n"
        f"**Likely range: {pert_subtotal}-{pessimistic_sum} hours**"
        f"{budget_block}\n\n"
        f"### Recommended team\n"
        f"{team_line}\n\n"
        f"### Estimated duration\n"
        f"{duration_line}\n\n"
        f"### Risks\n"
        f"{risks_block}\n\n"
        f"### Confidence\n"
        f"{draft.confidence}. {draft.confidence_rationale}  \n"
        f"Estimate valid for {draft.validity_days} days."
    )
