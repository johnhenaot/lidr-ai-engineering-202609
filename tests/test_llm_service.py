import pytest

from app.services import llm_service
from app.services.llm_service import (
    ESTIMATION_RULES,
    EXAMPLES_INTRO,
    OUTPUT_RULES,
    ROLE,
    SCOPE_RULES,
    build_system_prompt,
)


class TestBuildSystemPrompt:
    @pytest.fixture
    def fake_examples(self, monkeypatch):
        fakes = [
            {
                "meeting_summary": "  Client needs a CRM.  \n",
                "estimation": "\n## Estimate: CRM\n",
            },
            {
                "meeting_summary": "Second",
                "estimation": "## Estimate: Second",
            },
        ]
        monkeypatch.setattr(llm_service, "ESTIMATION_EXAMPLES", fakes)
        return fakes

    def test_assembles_sections_in_order(self, fake_examples):
        """Assemble sections in role, rules, examples, and output order."""
        prompt = build_system_prompt()
        sections = [
            ROLE,
            ESTIMATION_RULES,
            SCOPE_RULES,
            EXAMPLES_INTRO,
            "<examples>",
            OUTPUT_RULES,
        ]
        positions = [prompt.index(s) for s in sections]

        assert positions == sorted(positions)

    def test_formats_examples_with_xml_tags_and_stripped_content(self, fake_examples):
        """Format each example with 1-based id tag and stripped whitespace."""
        prompt = build_system_prompt()

        expected_block = (
            '<example id="1">\n'
            "<meeting_summary>\nClient needs a CRM.\n</meeting_summary>\n"
            "<estimation>\n## Estimate: CRM\n</estimation>\n"
            "</example>\n"
            '<example id="2">\n'
            "<meeting_summary>\nSecond\n</meeting_summary>\n"
            "<estimation>\n## Estimate: Second\n</estimation>\n"
            "</example>"
        )
        assert f"<examples>\n{expected_block}\n</examples>" in prompt

    def test_includes_role(self):
        """Include role definition in prompt."""
        assert ROLE in build_system_prompt()

    def test_includes_estimation_rules(self):
        """Include estimation rules in prompt."""
        assert ESTIMATION_RULES in build_system_prompt()

    def test_includes_scope_rules(self):
        """Include scope rules in prompt."""
        assert SCOPE_RULES in build_system_prompt()

    def test_includes_examples_intro(self):
        """Include raw transcript bridging instructions in prompt."""
        assert EXAMPLES_INTRO in build_system_prompt()

    def test_includes_output_rules(self):
        """Include output format rules in prompt."""
        assert OUTPUT_RULES in build_system_prompt()
