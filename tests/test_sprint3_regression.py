"""Sprint 3 Regression Pack.

Covers every change made in this sprint:

A) Clear-after-run (Task 1 — JS behaviour encoded as source-level assertions)
   - runReview() must contain the three clear-state lines after the error guard.

B) Persona YAML prompts (Task 2)
   - All 6 active group YAMLs load cleanly and contain the expected role labels.

C) AdminConfig.persona_prompts (Task 3)
   - Field present, default empty dict, load/save round-trip, update_config merge,
     null clears an override, to_safe_dict includes the field.

D) engine.py — list_roles + _build_prompt (Task 4)
   - list_roles() exposes prompt_template for every role.
   - YAML default is used when no admin override exists.
   - Admin override replaces the YAML default in list_roles() and _build_prompt().
   - Clearing the override (None) restores the YAML default.

E) HTML static analysis updates (Tasks 5 + 6)
   - savePersonaPrompts and resetPersonaPrompt functions are defined.
   - _getBaselinePrompt no longer only shows `purpose` (has prompt_template logic).
   - No new script-in-template regressions introduced.
"""

import re
import sys
import threading
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

HTML_PATH = Path(__file__).parent.parent / "static" / "index.html"
DEFS_DIR  = Path(__file__).parent.parent / "personas" / "definitions"


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Fresh temp dir + isolated DB thread-local for every test."""
    monkeypatch.setenv("PROJECTS_DATA_DIR", str(tmp_path))
    import db.database as _db
    import admin.config as _ac
    _db._BASE_DIR = tmp_path
    _db._thread_local = threading.local()
    # Point AdminConfig at the temp dir so tests never touch real config files
    _ac.CONFIG_DIR  = tmp_path
    _ac.CONFIG_FILE = tmp_path / "admin_config.json"
    yield


@pytest.fixture(scope="module")
def html_text():
    return HTML_PATH.read_text(encoding="utf-8")


# ══════════════════════════════════════════════════════════════════════════════
# A) Clear-after-run (Task 1)
# ══════════════════════════════════════════════════════════════════════════════

class TestClearAfterRun:
    """runReview() must reset the prompt builder state after a successful submission."""

    def test_injected_questions_cleared_after_run(self, html_text):
        """state._injectedQuestions=[] appears after the error guard in runReview()."""
        # Locate the runReview function body
        m = re.search(
            r"async function runReview\(\)(.*?)^(?:async function|\}$)",
            html_text, re.DOTALL | re.MULTILINE,
        )
        assert m, "runReview() function not found in index.html"
        body = m.group(1)

        # The error guard comes before the clear
        error_guard_pos  = body.find("if(r.error)")
        clear_pos        = body.find("state._injectedQuestions=[]")
        assert clear_pos != -1, (
            "state._injectedQuestions=[] not found inside runReview() — "
            "injected questions are never cleared after a successful run."
        )
        assert clear_pos > error_guard_pos, (
            "state._injectedQuestions=[] must appear AFTER the error guard, "
            "not before (should only clear on success)."
        )

    def test_render_injected_called_after_clear(self, html_text):
        """_renderInjectedQuestions() is called right after the clear."""
        m = re.search(
            r"async function runReview\(\)(.*?)^(?:async function|\}$)",
            html_text, re.DOTALL | re.MULTILINE,
        )
        assert m, "runReview() not found"
        body = m.group(1)
        clear_pos  = body.find("state._injectedQuestions=[]")
        render_pos = body.find("_renderInjectedQuestions()")
        assert render_pos != -1, "_renderInjectedQuestions() not called in runReview()"
        assert render_pos > clear_pos, (
            "_renderInjectedQuestions() must come after state._injectedQuestions=[]"
        )

    def test_userNotes_cleared_after_run(self, html_text):
        """userNotes textarea value is reset to '' after a successful run."""
        m = re.search(
            r"async function runReview\(\)(.*?)^(?:async function|\}$)",
            html_text, re.DOTALL | re.MULTILINE,
        )
        assert m, "runReview() not found"
        body = m.group(1)
        clear_pos = body.find("state._injectedQuestions=[]")
        notes_pos = body.find("notesEl.value=''")
        assert notes_pos != -1, (
            "notesEl.value='' not found in runReview() — userNotes is never cleared."
        )
        assert notes_pos > clear_pos, (
            "userNotes clear must come after state._injectedQuestions=[]"
        )


# ══════════════════════════════════════════════════════════════════════════════
# B) Persona YAML prompts (Task 2)
# ══════════════════════════════════════════════════════════════════════════════

ACTIVE_GROUP_YAMLS = {
    "architecture_strategy": {
        "roles": ["Solution Architect", "Enterprise Architect"],
        "prompt_contains": ["Solution Architect", "Enterprise Architect"],
    },
    "solution_delivery": {
        "roles": ["Delivery Manager"],
        "prompt_contains": ["Delivery Manager"],
    },
    "product_value": {
        "roles": ["Product Owner"],
        "prompt_contains": ["Product Owner"],
    },
    "people_capacity": {
        "roles": ["Resource Manager"],
        "prompt_contains": ["Resource Manager"],
    },
    "platform_reliability": {
        "roles": ["DevOps Engineer", "Cloud Architect", "Platform Engineer", "QA / Test Lead"],
        "prompt_contains": ["DevOps Engineer", "Cloud Architect", "Platform Engineer", "QA"],
    },
    "data_security_cost": {
        "roles": ["Data Engineer", "Security Architect", "FinOps"],
        "prompt_contains": ["Data Engineer", "Security Architect", "FinOps"],
    },
}


class TestPersonaYAMLPrompts:
    """All 6 active group YAMLs carry the new role-labelled prompts."""

    @pytest.mark.parametrize("group_id", list(ACTIVE_GROUP_YAMLS))
    def test_yaml_loads_cleanly(self, group_id):
        path = DEFS_DIR / f"{group_id}.yaml"
        assert path.exists(), f"{group_id}.yaml not found"
        data = yaml.safe_load(path.read_text())
        assert isinstance(data, dict), f"{group_id}.yaml did not parse to a dict"

    @pytest.mark.parametrize("group_id,spec", list(ACTIVE_GROUP_YAMLS.items()))
    def test_prompt_template_present_and_non_empty(self, group_id, spec):
        data = yaml.safe_load((DEFS_DIR / f"{group_id}.yaml").read_text())
        pt = data.get("prompt_template", "")
        assert pt and pt.strip(), f"{group_id}.yaml has empty prompt_template"

    @pytest.mark.parametrize("group_id,spec", list(ACTIVE_GROUP_YAMLS.items()))
    def test_prompt_contains_expected_role_labels(self, group_id, spec):
        data = yaml.safe_load((DEFS_DIR / f"{group_id}.yaml").read_text())
        pt = data.get("prompt_template", "")
        missing = [label for label in spec["prompt_contains"] if label not in pt]
        assert not missing, (
            f"{group_id}.yaml prompt_template missing expected labels: {missing}"
        )

    @pytest.mark.parametrize("group_id,spec", list(ACTIVE_GROUP_YAMLS.items()))
    def test_yaml_id_matches_filename(self, group_id, spec):
        data = yaml.safe_load((DEFS_DIR / f"{group_id}.yaml").read_text())
        assert data.get("id") == group_id, (
            f"{group_id}.yaml 'id' field is '{data.get('id')}', expected '{group_id}'"
        )


# ══════════════════════════════════════════════════════════════════════════════
# C) AdminConfig.persona_prompts (Task 3)
# ══════════════════════════════════════════════════════════════════════════════

class TestAdminConfigPersonaPrompts:

    def test_field_exists_on_dataclass(self):
        from admin.config import AdminConfig
        import dataclasses
        fields = {f.name for f in dataclasses.fields(AdminConfig)}
        assert "persona_prompts" in fields

    def test_default_is_empty_dict(self):
        from admin.config import AdminConfig
        cfg = AdminConfig()
        assert cfg.persona_prompts == {}

    def test_load_config_default_is_empty_dict(self):
        from admin.config import load_config
        cfg = load_config()
        assert cfg.persona_prompts == {}

    def test_save_and_reload_round_trip(self):
        from admin.config import load_config, update_config
        update_config({"persona_prompts": {"architecture_strategy": "CUSTOM PROMPT"}})
        cfg = load_config()
        assert cfg.persona_prompts["architecture_strategy"] == "CUSTOM PROMPT"

    def test_update_merges_per_group(self):
        from admin.config import update_config
        update_config({"persona_prompts": {"architecture_strategy": "P1"}})
        cfg = update_config({"persona_prompts": {"solution_delivery": "P2"}})
        assert cfg.persona_prompts["architecture_strategy"] == "P1"
        assert cfg.persona_prompts["solution_delivery"] == "P2"

    def test_null_clears_a_single_override(self):
        from admin.config import update_config
        update_config({"persona_prompts": {"architecture_strategy": "P1", "solution_delivery": "P2"}})
        cfg = update_config({"persona_prompts": {"architecture_strategy": None}})
        assert "architecture_strategy" not in cfg.persona_prompts
        assert cfg.persona_prompts["solution_delivery"] == "P2"

    def test_to_safe_dict_includes_persona_prompts(self):
        from admin.config import load_config
        d = load_config().to_safe_dict()
        assert "persona_prompts" in d

    def test_empty_string_stored_as_override(self):
        """An empty-string value is distinct from None; backend should store it."""
        from admin.config import update_config, load_config
        update_config({"persona_prompts": {"product_value": ""}})
        cfg = load_config()
        # Empty string is stored — backend treats it as 'no text entered', not a clear
        assert "product_value" in cfg.persona_prompts


# ══════════════════════════════════════════════════════════════════════════════
# D) engine.py list_roles + _build_prompt (Task 4)
# ══════════════════════════════════════════════════════════════════════════════

class TestEnginePromptOverride:

    def test_list_roles_includes_prompt_template_key(self):
        from personas.engine import list_roles
        roles = list_roles()
        for r in roles:
            assert "prompt_template" in r, (
                f"role '{r['id']}' missing prompt_template in list_roles() output"
            )

    def test_list_roles_prompt_template_non_empty(self):
        from personas.engine import list_roles
        roles = list_roles()
        empty = [r["id"] for r in roles if not r["prompt_template"].strip()]
        assert not empty, f"Roles with empty prompt_template: {empty}"

    def test_list_roles_yaml_default_contains_role_label(self):
        """Each role's prompt_template (YAML default, no override) names the role."""
        from admin.config import load_config, save_config
        # Ensure no overrides
        cfg = load_config()
        cfg.persona_prompts = {}
        save_config(cfg)

        from personas.engine import list_roles
        roles = list_roles()
        # Check a representative subset
        for expected_role in ["Solution Architect", "Delivery Manager", "Resource Manager"]:
            r = next((x for x in roles if x["id"] == expected_role), None)
            assert r is not None, f"Role '{expected_role}' not found"
            assert expected_role in r["prompt_template"], (
                f"'{expected_role}' not in its own prompt_template: "
                f"{r['prompt_template'][:100]}"
            )

    def test_admin_override_appears_in_list_roles(self):
        from admin.config import update_config
        from personas.engine import list_roles
        update_config({"persona_prompts": {"architecture_strategy": "ADMIN OVERRIDE TEXT"}})
        roles = list_roles()
        r = next(x for x in roles if x["id"] == "Solution Architect")
        assert r["prompt_template"] == "ADMIN OVERRIDE TEXT"

    def test_admin_override_used_in_build_prompt(self):
        from admin.config import update_config
        from personas.engine import _load_group, _build_prompt
        update_config({"persona_prompts": {"architecture_strategy": "INJECTED CUSTOM PROMPT"}})
        persona = _load_group("architecture_strategy")
        context = {
            "scope": "test", "risks": [], "assumptions": [], "dependencies": [],
            "constraints": [], "resources": [], "action_items": [],
        }
        prompt = _build_prompt(persona, ["Solution Architect"], context, None)
        assert "INJECTED CUSTOM PROMPT" in prompt, (
            "Admin override not present in built prompt"
        )

    def test_yaml_default_used_when_no_override(self):
        from admin.config import load_config, save_config
        from personas.engine import _load_group, _build_prompt
        cfg = load_config()
        cfg.persona_prompts = {}
        save_config(cfg)

        persona = _load_group("solution_delivery")
        context = {
            "scope": "test", "risks": [], "assumptions": [], "dependencies": [],
            "constraints": [], "resources": [], "action_items": [],
        }
        prompt = _build_prompt(persona, ["Delivery Manager"], context, None)
        assert "Delivery Manager" in prompt, (
            "YAML default prompt not used when no admin override exists"
        )

    def test_clearing_override_restores_yaml_default(self):
        from admin.config import update_config
        from personas.engine import list_roles
        # Set then clear
        update_config({"persona_prompts": {"solution_delivery": "TEMP OVERRIDE"}})
        update_config({"persona_prompts": {"solution_delivery": None}})
        roles = list_roles()
        r = next(x for x in roles if x["id"] == "Delivery Manager")
        assert "Delivery Manager" in r["prompt_template"], (
            "YAML default not restored after clearing admin override"
        )
        assert "TEMP OVERRIDE" not in r["prompt_template"]

    def test_override_does_not_affect_other_groups(self):
        from admin.config import update_config
        from personas.engine import list_roles
        update_config({"persona_prompts": {"architecture_strategy": "ARCH ONLY"}})
        roles = list_roles()
        dm = next(x for x in roles if x["id"] == "Delivery Manager")
        assert "ARCH ONLY" not in dm["prompt_template"], (
            "Architecture override leaked into Delivery Manager prompt"
        )


# ══════════════════════════════════════════════════════════════════════════════
# E) HTML static analysis updates (Tasks 5 + 6)
# ══════════════════════════════════════════════════════════════════════════════

class TestAdminFrontendFunctions:
    """New JS functions from tasks 5 and 6 must be defined in index.html."""

    REQUIRED = ["savePersonaPrompts", "resetPersonaPrompt"]

    def test_new_admin_functions_defined(self, html_text):
        missing = []
        for fn in self.REQUIRED:
            pattern = rf"(?:async\s+)?function\s+{re.escape(fn)}\s*\("
            if not re.search(pattern, html_text):
                missing.append(fn)
        assert not missing, (
            "Admin helper function(s) missing from index.html:\n"
            + "\n".join(f"  • {fn}" for fn in missing)
        )

    def test_persona_prompts_card_container_present(self, html_text):
        """The persona prompts result div is rendered."""
        assert 'id="personaPromptsResult"' in html_text, (
            'id="personaPromptsResult" not found — Admin Persona Prompts card missing'
        )

    def test_baseline_prompt_shows_prompt_template(self, html_text):
        """_getBaselinePrompt must reference prompt_template, not just purpose."""
        m = re.search(
            r"async function _getBaselinePrompt\(.*?\)\s*\{(.*?)\n\}",
            html_text, re.DOTALL,
        )
        assert m, "_getBaselinePrompt() not found in index.html"
        body = m.group(1)
        assert "prompt_template" in body, (
            "_getBaselinePrompt() does not reference prompt_template — "
            "it will still show only the purpose line, not the actual base prompt."
        )

    def test_baseline_prompt_no_longer_only_shows_purpose(self, html_text):
        """The primary path must use prompt_template; purpose is only a fallback."""
        m = re.search(
            r"async function _getBaselinePrompt\(.*?\)\s*\{(.*?)\n\}",
            html_text, re.DOTALL,
        )
        assert m, "_getBaselinePrompt() not found"
        body = m.group(1)
        # The primary push must be `lines.push(template)` — not purpose.
        # Accept either the bare push or one inside an if(template) block.
        assert re.search(r"lines\.push\(template\)", body), (
            "_getBaselinePrompt() primary path does not push `template` — "
            "it should push the prompt_template, with purpose only as fallback."
        )
        # The purpose push must only appear inside an else/fallback block,
        # confirming it is not the primary code path.
        purpose_match = re.search(r"lines\.push\(`\[.*?\]\$\{purpose", body)
        template_match = re.search(r"lines\.push\(template\)", body)
        if purpose_match and template_match:
            # purpose must come AFTER template in the source (i.e. in the else branch)
            assert purpose_match.start() > template_match.start(), (
                "purpose push appears before template push — "
                "purpose should only be in the else/fallback branch."
            )

    def test_no_script_in_template_literal_regression(self, html_text):
        """No new script-in-template-literal has been introduced."""
        script_blocks = []
        for m in re.finditer(r"<script[^>]*>(.*?)</script>", html_text,
                             re.DOTALL | re.IGNORECASE):
            script_blocks.append(m.group(1))

        violations = []
        for js in script_blocks:
            parts = re.split(r"(?<!\\)`", js)
            for i, part in enumerate(parts):
                if i % 2 == 1:
                    if re.search(r"<script[\s>]", part, re.IGNORECASE):
                        violations.append(part[:80])
        assert not violations, (
            "script-in-template-literal regression detected:\n"
            + "\n".join(f"  • {v}" for v in violations)
        )
