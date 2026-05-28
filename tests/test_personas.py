"""Tests for persona definitions and engine."""

from pathlib import Path

import yaml

PERSONAS_DIR = Path(__file__).parent.parent / "personas" / "definitions"


class TestPersonaDefinitions:
    """Validate all persona YAML files are well-formed."""

    def test_all_persona_files_exist(self):
        expected = [
            "solution_architect.yaml",
            "delivery_manager.yaml",
            "product_owner.yaml",
            "resource_manager.yaml",
        ]
        for name in expected:
            assert (PERSONAS_DIR / name).exists(), f"Missing persona: {name}"

    def test_personas_have_required_fields(self):
        required_fields = ["name", "role", "focus_areas", "output_format", "prompt_template"]
        for yaml_file in PERSONAS_DIR.glob("*.yaml"):
            with open(yaml_file) as f:
                persona = yaml.safe_load(f)
            for field in required_fields:
                assert field in persona, f"{yaml_file.name} missing field: {field}"

    def test_personas_have_focus_areas(self):
        for yaml_file in PERSONAS_DIR.glob("*.yaml"):
            with open(yaml_file) as f:
                persona = yaml.safe_load(f)
            assert len(persona["focus_areas"]) >= 3, (
                f"{yaml_file.name} needs at least 3 focus areas"
            )

    def test_personas_have_output_sections(self):
        for yaml_file in PERSONAS_DIR.glob("*.yaml"):
            with open(yaml_file) as f:
                persona = yaml.safe_load(f)
            sections = persona["output_format"]["sections"]
            assert len(sections) >= 3, f"{yaml_file.name} needs at least 3 output sections"

    def test_prompt_template_not_empty(self):
        for yaml_file in PERSONAS_DIR.glob("*.yaml"):
            with open(yaml_file) as f:
                persona = yaml.safe_load(f)
            assert len(persona["prompt_template"].strip()) > 50, (
                f"{yaml_file.name} prompt template too short"
            )
