"""Few-shot data that contradicts itself teaches the model to contradict itself."""

import re

import pytest

from app.context.examples import ESTIMATION_EXAMPLES

TASK_ROW = re.compile(r"^\| ([^|]+?) \| (\d+) \| (\d+) \| (\d+) \| (\d+) \|$", re.M)


def find(pattern: str, text: str) -> re.Match[str]:
    match = re.search(pattern, text)
    assert match, f"missing line matching {pattern!r}"
    return match


@pytest.fixture(params=ESTIMATION_EXAMPLES, ids=lambda e: e["estimation"].split("\n")[1])
def estimation(request) -> str:
    return request.param["estimation"]


def test_there_are_at_least_two_examples():
    assert len(ESTIMATION_EXAMPLES) >= 2


def test_every_example_has_both_halves():
    for example in ESTIMATION_EXAMPLES:
        assert example["meeting_summary"].strip(), "the client request must not be empty"
        assert example["estimation"].strip(), "the estimation must not be empty"


def test_breakdown_is_granular_enough(estimation: str):
    assert len(TASK_ROW.findall(estimation)) >= 5, "'build the platform' is not estimable"


def test_three_point_values_widen(estimation: str):
    for name, optimistic, likely, pessimistic, _ in TASK_ROW.findall(estimation):
        assert int(optimistic) < int(likely) < int(pessimistic), f"{name}: bad three-point spread"


def test_pert_column_matches_the_formula(estimation: str):
    for name, optimistic, likely, pessimistic, pert in TASK_ROW.findall(estimation):
        expected = round((int(optimistic) + 4 * int(likely) + int(pessimistic)) / 6)
        assert expected == int(pert), f"{name}: PERT should be {expected}"


def test_tasks_sum_to_the_stated_subtotal(estimation: str):
    tasks = sum(int(row[4]) for row in TASK_ROW.findall(estimation))
    stated = int(find(r"PERT subtotal: (\d+)", estimation).group(1))

    assert tasks == stated


def test_contingency_is_explicit_and_within_the_recommended_band(estimation: str):
    percent = int(find(r"Contingency \((\d+)%\)", estimation).group(1))
    buffer_hours = int(find(r"Contingency \(\d+%\): (\d+)", estimation).group(1))
    subtotal = int(find(r"PERT subtotal: (\d+)", estimation).group(1))

    assert 15 <= percent <= 25
    assert round(subtotal * percent / 100) == buffer_hours


def test_total_is_subtotal_plus_contingency(estimation: str):
    subtotal = int(find(r"PERT subtotal: (\d+)", estimation).group(1))
    buffer_hours = int(find(r"Contingency \(\d+%\): (\d+)", estimation).group(1))
    total = int(find(r"Total estimate: (\d+)", estimation).group(1))

    assert subtotal + buffer_hours == total


def test_the_estimate_is_a_range_containing_the_total(estimation: str):
    low, high = (int(v) for v in find(r"Likely range: (\d+)-(\d+)", estimation).groups())
    total = int(find(r"Total estimate: (\d+)", estimation).group(1))

    assert low < total < high, "a point estimate at proposal stage is false precision"


@pytest.mark.parametrize(
    "section", ["### Assumptions", "### Out of scope", "### Risks", "### Confidence"]
)
def test_required_sections_are_present(estimation: str, section: str):
    assert section in estimation


def test_examples_differ_in_confidence():
    """The pair must teach that uncertainty widens the range, not one fixed shape."""
    spreads = []
    for example in ESTIMATION_EXAMPLES:
        low, high = (int(v) for v in find(r"Likely range: (\d+)-(\d+)", example["estimation"]).groups())
        spreads.append((high - low) / low)

    assert max(spreads) > min(spreads) * 1.2, "all examples carry the same uncertainty"
