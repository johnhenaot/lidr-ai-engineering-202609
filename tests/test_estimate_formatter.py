import pytest

from app.domain.estimate import (
    Duration,
    EstimateDraft,
    HourlyRate,
    Risk,
    TaskDraft,
    TeamMember,
)
from app.services.estimate_formatter import render_markdown


def make_draft(**overrides) -> EstimateDraft:
    defaults = {
        "meeting_summary": "Client needs a portal.",
        "estimate_title": "Portal Project",
        "assumptions": ["API docs provided."],
        "out_of_scope": ["Mobile app."],
        "tasks": [TaskDraft(name="Core", optimistic=10, likely=20, pessimistic=30)],
        "team": [TeamMember(role="engineers", quantity=2, details="")],
        "duration": Duration(floor=2, ceiling=4, unit="weeks"),
        "risks": [Risk(label="Risk1", impact="low", detail="Minimal.")],
        "confidence": "High",
        "confidence_rationale": "Clear scope.",
        "validity_days": 30,
    }
    defaults.update(overrides)
    return EstimateDraft(**defaults)


class TestRenderMarkdownSections:
    def test_renders_all_required_section_headings_in_house_order(self):
        """Render all required markdown section headings in house order."""
        output = render_markdown(make_draft())

        sections = [
            "## Estimate: Portal Project",
            "### Assumptions",
            "### Out of scope",
            "### Task breakdown (three-point estimation, hours)",
            "### Recommended team",
            "### Estimated duration",
            "### Risks",
            "### Confidence",
            "Estimate valid for 30 days.",
        ]
        positions = [output.index(s) for s in sections]

        assert positions == sorted(positions)

    def test_renders_assumptions_and_out_of_scope_items_as_bullets(self):
        """Render assumptions and out of scope items as markdown bullet lists."""
        output = render_markdown(
            make_draft(
                assumptions=["First assumption."],
                out_of_scope=["Excluded feature."],
            )
        )

        assert "- First assumption." in output
        assert "- Excluded feature." in output

    def test_renders_risks_with_label_impact_and_detail(self):
        """Render risk items with bold label, parenthetical impact, and detail."""
        output = render_markdown(
            make_draft(
                risks=[
                    Risk(label="Data loss", impact="high", detail="Backup required.")
                ]
            )
        )

        assert "- **Data loss (high):** Backup required." in output

    def test_omits_meeting_summary_from_rendered_markdown(self):
        """Exclude internal meeting summary scratchpad from rendered output."""
        output = render_markdown(make_draft(meeting_summary="Secret meeting notes."))

        assert "Secret meeting notes." not in output


class TestRenderMarkdownTaskTable:
    @pytest.mark.parametrize(
        ("optimistic", "likely", "pessimistic", "expected_pert"),
        [
            (10, 20, 30, 20),
            (1, 2, 6, 3),
            (2, 2, 5, 3),
            (28, 40, 60, 41),
            (45, 60, 88, 62),
        ],
    )
    def test_renders_task_row_with_computed_pert(
        self, optimistic, likely, pessimistic, expected_pert
    ):
        """Render task row with arithmetically computed PERT value."""
        draft = make_draft(
            tasks=[
                TaskDraft(
                    name="Task",
                    optimistic=optimistic,
                    likely=likely,
                    pessimistic=pessimistic,
                )
            ]
        )

        output = render_markdown(draft)

        assert (
            f"| Task | {optimistic} | {likely} | {pessimistic} | {expected_pert} |"
            in output
        )


class TestRenderMarkdownTotals:
    def test_calculates_twenty_percent_contingency_for_high_confidence(self):
        """Render 20% contingency and derived total for High confidence."""
        draft = make_draft(
            tasks=[TaskDraft(name="T", optimistic=10, likely=20, pessimistic=30)],
            confidence="High",
        )

        output = render_markdown(draft)

        assert "**PERT subtotal: 20 hours**" in output
        assert "**Contingency (20%): 4 hours**" in output
        assert "**Total estimate: 24 hours**" in output
        assert "**Likely range: 20-30 hours**" in output

    def test_calculates_twenty_three_percent_contingency_for_medium_confidence(
        self,
    ):
        """Render 23% contingency and derived total for Medium confidence."""
        draft = make_draft(
            tasks=[TaskDraft(name="T", optimistic=100, likely=100, pessimistic=100)],
            confidence="Medium",
        )

        output = render_markdown(draft)

        assert "**PERT subtotal: 100 hours**" in output
        assert "**Contingency (23%): 23 hours**" in output
        assert "**Total estimate: 123 hours**" in output

    def test_calculates_twenty_five_percent_contingency_for_low_confidence(self):
        """Render 25% contingency and derived total for Low confidence."""
        draft = make_draft(
            tasks=[TaskDraft(name="T", optimistic=100, likely=100, pessimistic=100)],
            confidence="Low",
        )

        output = render_markdown(draft)

        assert "**PERT subtotal: 100 hours**" in output
        assert "**Contingency (25%): 25 hours**" in output
        assert "**Total estimate: 125 hours**" in output

    def test_rounds_contingency_half_integers_up(self):
        """Round contingency half-integers up to the nearest hour in totals."""
        draft = make_draft(
            tasks=[TaskDraft(name="T", optimistic=322, likely=322, pessimistic=322)],
            confidence="Low",
        )

        output = render_markdown(draft)

        assert "**Contingency (25%): 81 hours**" in output

    def test_renders_accumulated_totals_for_multiple_tasks(self):
        """Render accumulated subtotal, contingency, total, and range across tasks."""
        draft = make_draft(
            tasks=[
                TaskDraft(name="T1", optimistic=10, likely=20, pessimistic=30),
                TaskDraft(name="T2", optimistic=4, likely=6, pessimistic=14),
            ],
            confidence="High",
        )

        output = render_markdown(draft)

        assert "**PERT subtotal: 27 hours**" in output
        assert "**Contingency (20%): 5 hours**" in output
        assert "**Total estimate: 32 hours**" in output
        assert "**Likely range: 27-44 hours**" in output


class TestRenderMarkdownTeam:
    def test_formats_member_without_details(self):
        """Render team member without parenthetical details when details is empty."""
        draft = make_draft(
            team=[TeamMember(role="full-stack developers", quantity=2, details="")]
        )

        output = render_markdown(draft)

        assert "2 full-stack developers\n" in output

    def test_formats_member_with_details(self):
        """Render team member with parenthetical details when details is present."""
        draft = make_draft(
            team=[
                TeamMember(
                    role="UX designer",
                    quantity=1,
                    details="part-time, first 3 weeks",
                )
            ]
        )

        output = render_markdown(draft)

        assert "1 UX designer (part-time, first 3 weeks)\n" in output

    def test_joins_multiple_members_with_plus_sign(self):
        """Render multiple team members joined by plus sign."""
        draft = make_draft(
            team=[
                TeamMember(role="full-stack developers", quantity=2, details=""),
                TeamMember(
                    role="UX designer",
                    quantity=1,
                    details="part-time, first 3 weeks",
                ),
            ]
        )

        output = render_markdown(draft)

        assert (
            "2 full-stack developers + 1 UX designer (part-time, first 3 weeks)\n"
            in output
        )


class TestRenderMarkdownDuration:
    def test_formats_range_when_floor_and_ceiling_differ(self):
        """Render duration as hyphenated range when floor and ceiling differ."""
        draft = make_draft(duration=Duration(floor=6, ceiling=8, unit="weeks"))

        output = render_markdown(draft)

        assert "6-8 weeks\n" in output

    def test_formats_single_number_when_floor_equals_ceiling(self):
        """Render duration as single number when floor equals ceiling."""
        draft = make_draft(duration=Duration(floor=4, ceiling=4, unit="weeks"))

        output = render_markdown(draft)

        assert "4 weeks\n" in output


class TestRenderMarkdownBudget:
    def test_omits_budget_block_when_rate_is_none(self):
        """Omit budget block when no hourly rate is provided."""
        output = render_markdown(make_draft(rate=None))

        assert "### Budget" not in output

    def test_renders_budget_block_when_rate_is_present(self):
        """Render total cost and range based on hourly rate."""
        draft = make_draft(
            tasks=[TaskDraft(name="T", optimistic=10, likely=20, pessimistic=30)],
            rate=HourlyRate(amount=120.0, currency="USD"),
        )
        output = render_markdown(draft)

        assert "### Budget (120.00 USD/hour)" in output
        assert "**Total: 2,880.00 USD**" in output
        assert "**Likely range: 2,400.00-3,600.00 USD**" in output

    def test_renders_fractional_hourly_rate_with_two_decimal_places(self):
        """Render fractional hourly rate with two decimal places."""
        draft = make_draft(
            tasks=[TaskDraft(name="T", optimistic=10, likely=20, pessimistic=30)],
            rate=HourlyRate(amount=87.5, currency="EUR"),
        )
        output = render_markdown(draft)

        assert "### Budget (87.50 EUR/hour)" in output
        assert "**Total: 2,100.00 EUR**" in output
        assert "**Likely range: 1,750.00-2,625.00 EUR**" in output
