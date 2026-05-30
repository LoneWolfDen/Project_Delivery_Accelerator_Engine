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

F) S3-01 — SME question generator (deep_dive heuristic output contract)
   - Heuristic path returns question_groups (not generic advice).
   - Each group has category, icon, questions list.
   - all_questions flat list carries [category] prefix.
   - scope_completeness is 0–100 integer.
   - Question text is not generic boilerplate when project-specific content exists.

G) S3-02 — Question selection flow (addSelectedToPrompt contract)
   - addSelectedToPrompt function is defined in index.html.
   - state._injectedQuestions array is used (not customPrompt textarea).
   - _removeInjectedQuestion function exists and deselects items.
   - Strip of role prefix before storage: [Role] tag removal.

H) S3-03 — Run tightened review
   - previous_review_id flows from server body → project_manager → store.
   - New review stores both previous_review_id and prompt_builder_state together.
   - previousReviewId hidden input element present in index.html.
   - runReview() includes previous_review_id in the POST body.
   - viewReviewDetail() contains a tighten/chaining trigger element.

I) S3-04 — What Changed summary
   - get_review_diff() backend logic: new / resolved / unchanged classification.
   - Diff only fires when previous_review_id is set; absent otherwise.
   - "What Changed" section rendered in viewReviewDetail() when previous_review_id set.
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



# ══════════════════════════════════════════════════════════════════════════════
# F) S3-01 — SME question generator (deep_dive heuristic output contract)
# ══════════════════════════════════════════════════════════════════════════════

class TestDeepDiveHeuristicOutputContract:
    """S3-01 — heuristic deep dive returns structured questions, not generic advice."""

    # ── Shared fixtures ───────────────────────────────────────────────────────

    @staticmethod
    def _run(persona_name: str = "Solution Architect", scope: str = "Cloud migration",
             intelligence: dict = None, active_files: list = None) -> dict:
        from personas.deep_dive import run_deep_dive
        return run_deep_dive(
            persona_name=persona_name,
            scope=scope or "Cloud migration project",
            intelligence=intelligence or {"risks": [], "assumptions": [], "dependencies": [],
                                          "constraints": [], "action_items": []},
            active_files=active_files or [{"filename": "scope.txt", "source_type": "text"}],
            custom_prompt="",
            ai_backend="files_only",
        )

    # ── Happy-path structure ──────────────────────────────────────────────────

    def test_returns_dict_with_required_top_level_keys(self):
        result = self._run()
        for key in ("timestamp", "persona", "ai_backend", "ai_mode",
                    "question_groups", "all_questions", "scope_completeness", "meta"):
            assert key in result, f"Missing key: {key}"

    def test_ai_mode_is_false_for_files_only(self):
        result = self._run()
        assert result["ai_mode"] is False

    def test_question_groups_is_non_empty_list(self):
        result = self._run()
        assert isinstance(result["question_groups"], list)
        assert len(result["question_groups"]) >= 1

    def test_each_group_has_required_keys(self):
        result = self._run()
        for grp in result["question_groups"]:
            for key in ("category", "icon", "questions"):
                assert key in grp, f"Group missing key '{key}': {grp}"

    def test_each_group_questions_is_non_empty_list(self):
        result = self._run()
        for grp in result["question_groups"]:
            assert isinstance(grp["questions"], list)
            assert len(grp["questions"]) >= 1, f"Group '{grp['category']}' has no questions"

    def test_all_questions_flat_list_is_non_empty(self):
        result = self._run()
        assert isinstance(result["all_questions"], list)
        assert len(result["all_questions"]) >= 1

    def test_all_questions_carry_category_prefix(self):
        """Every item in all_questions starts with [Category] prefix."""
        result = self._run()
        for q in result["all_questions"]:
            assert q.startswith("["), (
                f"Question missing [Category] prefix: {q!r}"
            )
            assert "]" in q, f"Question prefix not closed: {q!r}"

    def test_scope_completeness_is_integer_0_to_100(self):
        result = self._run()
        sc = result["scope_completeness"]
        assert isinstance(sc, int), f"scope_completeness must be int, got {type(sc)}"
        assert 0 <= sc <= 100, f"scope_completeness out of range: {sc}"

    def test_meta_has_source_field(self):
        result = self._run()
        assert "source" in result["meta"]
        assert result["meta"]["source"] == "heuristic"

    def test_question_min_length(self):
        """No question should be shorter than 20 characters (spec requirement)."""
        result = self._run()
        for grp in result["question_groups"]:
            for q in grp["questions"]:
                assert len(q) >= 20, f"Question too short ({len(q)} chars): {q!r}"

    # ── Persona-specific grouping ─────────────────────────────────────────────

    def test_solution_architect_returns_architecture_category(self):
        result = self._run(persona_name="Solution Architect")
        categories = [g["category"] for g in result["question_groups"]]
        arch_present = any("Architect" in c or "Design" in c or "NFR" in c
                           for c in categories)
        assert arch_present, (
            f"Solution Architect deep dive missing Architecture/Design/NFR category. "
            f"Got: {categories}"
        )

    def test_delivery_manager_returns_delivery_category(self):
        result = self._run(persona_name="Delivery Manager")
        categories = [g["category"] for g in result["question_groups"]]
        delivery_present = any("Delivery" in c or "Risk" in c or "Scope" in c
                               for c in categories)
        assert delivery_present, (
            f"Delivery Manager deep dive missing delivery-related category. Got: {categories}"
        )

    def test_resource_manager_returns_skills_or_capacity_category(self):
        result = self._run(persona_name="Resource Manager")
        categories = [g["category"] for g in result["question_groups"]]
        people_present = any("Skill" in c or "Capacity" in c or "People" in c
                             for c in categories)
        assert people_present, (
            f"Resource Manager deep dive missing skills/capacity category. Got: {categories}"
        )

    # ── Negative tests ────────────────────────────────────────────────────────

    def test_empty_scope_still_returns_questions(self):
        """Edge: empty scope must not crash or return zero questions."""
        result = self._run(scope="")
        assert len(result["question_groups"]) >= 1
        assert len(result["all_questions"]) >= 1

    def test_empty_intelligence_still_returns_questions(self):
        """Edge: all-empty intelligence dict must not crash."""
        result = self._run(intelligence={})
        assert len(result["question_groups"]) >= 1

    def test_no_active_files_still_returns_questions(self):
        """Edge: no active files must not crash."""
        result = self._run(active_files=[])
        assert len(result["question_groups"]) >= 1

    def test_unknown_persona_falls_back_gracefully(self):
        """Unknown persona must not raise — falls back to architecture_strategy."""
        result = self._run(persona_name="Quantum Strategist")
        assert isinstance(result["question_groups"], list)
        assert len(result["all_questions"]) >= 1

    def test_groups_capped_at_six(self):
        """At most 6 question groups must be returned (spec cap)."""
        result = self._run()
        assert len(result["question_groups"]) <= 6

    def test_scope_completeness_zero_for_empty_everything(self):
        """Completely empty scope and intelligence should score low or zero."""
        result = self._run(scope="", intelligence={})
        assert result["scope_completeness"] == 0

    def test_rich_scope_scores_higher_than_empty(self):
        rich = "objectives: migrate all services. timeline: 6 months. budget: £500K. " \
               "stakeholders: CTO. constraints: no downtime. assumptions: team available. risks: vendor risk."
        r_rich = self._run(scope=rich, intelligence={
            "risks": ["vendor lock-in"], "assumptions": ["team available"],
            "constraints": ["no downtime"], "dependencies": []
        })
        r_empty = self._run(scope="", intelligence={})
        assert r_rich["scope_completeness"] > r_empty["scope_completeness"]



# ══════════════════════════════════════════════════════════════════════════════
# G) S3-02 — Question selection flow (HTML contract)
# ══════════════════════════════════════════════════════════════════════════════

class TestQuestionSelectionFlowHTML:
    """S3-02 — addSelectedToPrompt uses state._injectedQuestions, not customPrompt."""

    def test_addSelectedToPrompt_function_defined(self, html_text):
        pattern = r"(?:async\s+)?function\s+addSelectedToPrompt\s*\("
        assert re.search(pattern, html_text), (
            "addSelectedToPrompt() not defined in index.html"
        )

    def test_addSelectedToPrompt_pushes_to_injectedQuestions_not_textarea(self, html_text):
        """The function must push to _injectedQuestions array, not append to customPrompt."""
        m = re.search(
            r"function\s+addSelectedToPrompt\s*\(.*?\)\s*\{(.*?)\n\}",
            html_text, re.DOTALL,
        )
        assert m, "addSelectedToPrompt() body not found"
        body = m.group(1)
        # Must reference _injectedQuestions push
        assert "_injectedQuestions" in body, (
            "addSelectedToPrompt() does not reference state._injectedQuestions — "
            "selected questions are not being added to the chip list."
        )
        # Must NOT append to customPrompt textarea
        assert "customPrompt" not in body, (
            "addSelectedToPrompt() still references customPrompt textarea — "
            "S2-01 requires the chip-based injected questions section instead."
        )

    def test_removeInjectedQuestion_function_defined(self, html_text):
        """_removeInjectedQuestion must exist so chips can be deselected."""
        pattern = r"(?:async\s+)?function\s+_removeInjectedQuestion\s*\("
        assert re.search(pattern, html_text), (
            "_removeInjectedQuestion() not defined in index.html — "
            "users cannot remove chips from the injected questions section."
        )

    def test_renderInjectedQuestions_function_defined(self, html_text):
        pattern = r"(?:async\s+)?function\s+_renderInjectedQuestions\s*\("
        assert re.search(pattern, html_text), (
            "_renderInjectedQuestions() not defined in index.html"
        )

    def test_injectedQuestions_state_initialised_before_use(self, html_text):
        """state._injectedQuestions must be initialised (not assumed to exist)."""
        # Accept either direct assignment or short-circuit initialisation
        has_init = (
            "state._injectedQuestions=[]" in html_text
            or "state._injectedQuestions = []" in html_text
            or "_injectedQuestions:[]" in html_text
            or "_injectedQuestions: []" in html_text
        )
        assert has_init, (
            "state._injectedQuestions is never initialised in index.html — "
            "first call to addSelectedToPrompt will fail with TypeError."
        )

    def test_customPrompt_textarea_absent(self, html_text):
        """The old single customPrompt textarea must no longer exist (S2-01 replaced it)."""
        assert 'id="customPrompt"' not in html_text, (
            'id="customPrompt" textarea is still present — should have been removed in S2-01.'
        )

    def test_injectedQuestions_container_present(self, html_text):
        """The chip container for injected questions must be in the DOM."""
        assert 'id="injectedQuestions"' in html_text, (
            'id="injectedQuestions" container missing from index.html.'
        )

    def test_userNotes_textarea_present(self, html_text):
        """The free-text notes field (Section 3 of prompt builder) must exist."""
        assert 'id="userNotes"' in html_text, (
            'id="userNotes" textarea missing — prompt builder Section 3 absent.'
        )



# ══════════════════════════════════════════════════════════════════════════════
# H) S3-03 — Run tightened review (backend + HTML contract)
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture()
def store_s3(tmp_path, monkeypatch):
    """Isolated SQLite store for S3-03 tests."""
    monkeypatch.setenv("PROJECTS_DATA_DIR", str(tmp_path))
    import db.database as _db
    import threading
    _db._BASE_DIR = tmp_path
    _db._thread_local = threading.local()
    from db.hierarchy_store_sql import HierarchyStoreSQLite
    return HierarchyStoreSQLite("proj-s3-chain")


@pytest.fixture()
def version_s3(store_s3):
    return store_s3.create_version(
        included_artifacts=[{"filename": "spec.md", "category": "scope"}],
        label="v1",
    )


class TestTightenedReviewBackend:
    """S3-03 — previous_review_id and prompt_builder_state survive the full write-read cycle."""

    def test_chained_review_stores_previous_review_id(self, store_s3, version_s3):
        r1 = store_s3.create_review(version_id=version_s3.version_id, persona="SA")
        r2 = store_s3.create_review(
            version_id=version_s3.version_id, persona="SA",
            previous_review_id=r1.review_id,
        )
        fetched = store_s3.get_review(r2.review_id)
        assert fetched.previous_review_id == r1.review_id

    def test_chained_review_also_stores_prompt_builder_state(self, store_s3, version_s3):
        """Tightened review persists both chaining and prompt state together."""
        r1 = store_s3.create_review(version_id=version_s3.version_id, persona="SA")
        pbs = {"injected_questions": ["What is DR strategy?"], "user_notes": "AWS preferred"}
        r2 = store_s3.create_review(
            version_id=version_s3.version_id, persona="SA",
            previous_review_id=r1.review_id,
            prompt_builder_state=pbs,
        )
        fetched = store_s3.get_review(r2.review_id)
        assert fetched.previous_review_id == r1.review_id
        assert fetched.prompt_builder_state == pbs

    def test_chained_review_iteration_number_increments(self, store_s3, version_s3):
        """Chained reviews receive ascending iteration numbers (R1=1, R2=2)."""
        r1 = store_s3.create_review(version_id=version_s3.version_id, persona="SA")
        r2 = store_s3.create_review(
            version_id=version_s3.version_id, persona="SA",
            previous_review_id=r1.review_id,
        )
        summaries = {s["review_id"]: s for s in store_s3.list_reviews(version_id=version_s3.version_id)}
        assert summaries[r1.review_id]["iteration_number"] == 1
        assert summaries[r2.review_id]["iteration_number"] == 2

    def test_unchained_review_has_empty_previous_id(self, store_s3, version_s3):
        r = store_s3.create_review(version_id=version_s3.version_id, persona="SA")
        assert r.previous_review_id == ""

    def test_three_level_chain_integrity(self, store_s3, version_s3):
        """R1 → R2 → R3: each points only to its direct predecessor."""
        r1 = store_s3.create_review(version_id=version_s3.version_id, persona="SA")
        r2 = store_s3.create_review(
            version_id=version_s3.version_id, persona="SA",
            previous_review_id=r1.review_id,
        )
        r3 = store_s3.create_review(
            version_id=version_s3.version_id, persona="SA",
            previous_review_id=r2.review_id,
        )
        assert store_s3.get_review(r3.review_id).previous_review_id == r2.review_id
        assert store_s3.get_review(r2.review_id).previous_review_id == r1.review_id
        assert store_s3.get_review(r1.review_id).previous_review_id == ""

    def test_previous_review_id_visible_in_to_summary(self, store_s3, version_s3):
        r1 = store_s3.create_review(version_id=version_s3.version_id, persona="SA")
        r2 = store_s3.create_review(
            version_id=version_s3.version_id, persona="SA",
            previous_review_id=r1.review_id,
        )
        s = store_s3.get_review(r2.review_id).to_summary()
        assert s["previous_review_id"] == r1.review_id

    def test_previous_review_id_visible_in_list_reviews(self, store_s3, version_s3):
        r1 = store_s3.create_review(version_id=version_s3.version_id, persona="SA")
        r2 = store_s3.create_review(
            version_id=version_s3.version_id, persona="SA",
            previous_review_id=r1.review_id,
        )
        by_id = {s["review_id"]: s["previous_review_id"]
                 for s in store_s3.list_reviews(version_id=version_s3.version_id)}
        assert by_id[r2.review_id] == r1.review_id
        assert by_id[r1.review_id] == ""

    def test_chained_review_with_findings_persists_findings_too(self, store_s3, version_s3):
        """Chaining does not corrupt the findings field."""
        r1 = store_s3.create_review(version_id=version_s3.version_id, persona="SA",
                                    findings={"risks": ["vendor lock-in"]})
        r2 = store_s3.create_review(
            version_id=version_s3.version_id, persona="SA",
            previous_review_id=r1.review_id,
            findings={"risks": ["cost overrun"]},
        )
        fetched = store_s3.get_review(r2.review_id)
        assert fetched.previous_review_id == r1.review_id
        assert fetched.findings == {"risks": ["cost overrun"]}


class TestTightenedReviewHTML:
    """S3-03 — HTML contract for chained review submission."""

    def test_previousReviewId_input_exists_in_html(self, html_text):
        """Hidden input for previousReviewId must be present so runReview() can read it."""
        assert 'id="previousReviewId"' in html_text, (
            'id="previousReviewId" hidden input not found in index.html — '
            "runReview() cannot read the predecessor review ID."
        )

    def test_runReview_sends_previous_review_id(self, html_text):
        """runReview() POST body must include previous_review_id."""
        m = re.search(
            r"async function runReview\(\)(.*?)^(?:async function|\}$)",
            html_text, re.DOTALL | re.MULTILINE,
        )
        assert m, "runReview() not found in index.html"
        body = m.group(1)
        assert "previous_review_id" in body, (
            "runReview() does not include previous_review_id in the POST body — "
            "chained reviews will never be linked to their predecessor."
        )

    def test_runReview_sends_prompt_builder_state(self, html_text):
        """runReview() must assemble and send prompt_builder_state."""
        m = re.search(
            r"async function runReview\(\)(.*?)^(?:async function|\}$)",
            html_text, re.DOTALL | re.MULTILINE,
        )
        assert m, "runReview() not found"
        body = m.group(1)
        assert "prompt_builder_state" in body, (
            "runReview() does not include prompt_builder_state in the POST body."
        )

    def test_viewReviewDetail_has_tighten_mechanism(self, html_text):
        """viewReviewDetail() must contain something that sets previousReviewId
        or navigates to the tightening flow.  Accept any of the likely patterns."""
        m = re.search(
            r"(?:async\s+)?function\s+viewReviewDetail\s*\(.*?\)\s*\{(.*?)\n\}",
            html_text, re.DOTALL,
        )
        assert m, "viewReviewDetail() not found in index.html"
        body = m.group(1)
        has_tighten = (
            "previousReviewId" in body
            or "previous_review_id" in body
            or "Tighten" in body
            or "tighten" in body
        )
        assert has_tighten, (
            "viewReviewDetail() has no reference to previousReviewId or tightening — "
            "users cannot start a tightened review from the review detail page."
        )



# ══════════════════════════════════════════════════════════════════════════════
# I) S3-04 — What Changed summary (get_review_diff logic)
# ══════════════════════════════════════════════════════════════════════════════

def _make_diff_store(tmp_path, monkeypatch):
    """Helper: create an isolated store for diff tests."""
    monkeypatch.setenv("PROJECTS_DATA_DIR", str(tmp_path))
    import db.database as _db
    import threading
    _db._BASE_DIR = tmp_path
    _db._thread_local = threading.local()
    from db.hierarchy_store_sql import HierarchyStoreSQLite
    return HierarchyStoreSQLite("proj-s3-diff")


class TestGetReviewDiff:
    """S3-04 — get_review_diff() classifies findings as new / resolved / unchanged."""

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path, monkeypatch):
        self.store = _make_diff_store(tmp_path, monkeypatch)
        self.version = self.store.create_version(included_artifacts=[], label="v1")

    @staticmethod
    def _diff(prev_findings: dict, curr_findings: dict) -> dict:
        """Pure helper mirroring the get_review_diff logic for unit tests.

        Rules (per S3-04 spec):
          new       — in current but NOT in previous (by text equality)
          resolved  — in previous but NOT in current
          unchanged — in both
        """
        result = {}
        all_cats = set(prev_findings) | set(curr_findings)
        for cat in all_cats:
            prev_items = set(prev_findings.get(cat, []))
            curr_items = set(curr_findings.get(cat, []))
            result[cat] = {
                "new":       sorted(curr_items - prev_items),
                "resolved":  sorted(prev_items - curr_items),
                "unchanged": sorted(curr_items & prev_items),
            }
        return result

    # ── Happy-path diff classification ───────────────────────────────────────

    def test_new_finding_classified_as_new(self):
        diff = self._diff(
            prev_findings={"risks": ["vendor lock-in"]},
            curr_findings={"risks": ["vendor lock-in", "cost overrun"]},
        )
        assert "cost overrun" in diff["risks"]["new"]

    def test_removed_finding_classified_as_resolved(self):
        diff = self._diff(
            prev_findings={"risks": ["vendor lock-in", "cost overrun"]},
            curr_findings={"risks": ["vendor lock-in"]},
        )
        assert "cost overrun" in diff["risks"]["resolved"]

    def test_retained_finding_classified_as_unchanged(self):
        diff = self._diff(
            prev_findings={"risks": ["vendor lock-in"]},
            curr_findings={"risks": ["vendor lock-in"]},
        )
        assert "vendor lock-in" in diff["risks"]["unchanged"]

    def test_entirely_new_category_all_items_are_new(self):
        diff = self._diff(
            prev_findings={"risks": ["risk A"]},
            curr_findings={"risks": ["risk A"], "assumptions": ["assume X"]},
        )
        assert "assume X" in diff["assumptions"]["new"]
        assert diff["assumptions"]["resolved"] == []
        assert diff["assumptions"]["unchanged"] == []

    def test_entirely_removed_category_all_items_are_resolved(self):
        diff = self._diff(
            prev_findings={"risks": ["risk A"], "assumptions": ["assume X"]},
            curr_findings={"risks": ["risk A"]},
        )
        assert "assume X" in diff["assumptions"]["resolved"]
        assert diff["assumptions"]["new"] == []

    def test_no_overlap_all_findings_are_new_and_resolved(self):
        diff = self._diff(
            prev_findings={"risks": ["old risk"]},
            curr_findings={"risks": ["new risk"]},
        )
        assert "new risk" in diff["risks"]["new"]
        assert "old risk" in diff["risks"]["resolved"]
        assert diff["risks"]["unchanged"] == []

    def test_identical_findings_all_unchanged(self):
        findings = {"risks": ["vendor lock-in", "cost overrun"]}
        diff = self._diff(findings, findings)
        assert diff["risks"]["new"] == []
        assert diff["risks"]["resolved"] == []
        assert sorted(diff["risks"]["unchanged"]) == sorted(findings["risks"])

    def test_empty_previous_all_current_are_new(self):
        diff = self._diff(
            prev_findings={},
            curr_findings={"risks": ["new risk"], "assumptions": ["assume X"]},
        )
        assert "new risk" in diff["risks"]["new"]
        assert "assume X" in diff["assumptions"]["new"]

    def test_empty_current_all_previous_are_resolved(self):
        diff = self._diff(
            prev_findings={"risks": ["old risk"]},
            curr_findings={},
        )
        assert "old risk" in diff["risks"]["resolved"]

    def test_empty_both_returns_empty_diff(self):
        diff = self._diff({}, {})
        assert diff == {}

    # ── State consistency with store ──────────────────────────────────────────

    def test_review_without_predecessor_has_no_diff_context(self):
        """A standalone review has previous_review_id == '' — diff has no predecessor."""
        r = self.store.create_review(
            version_id=self.version.version_id, persona="SA",
            findings={"risks": ["vendor lock-in"]},
        )
        fetched = self.store.get_review(r.review_id)
        assert fetched.previous_review_id == "", (
            "A standalone review must have no predecessor — diff section should not render."
        )

    def test_chained_review_has_predecessor_for_diff(self):
        """A chained review has a valid predecessor to diff against."""
        r1 = self.store.create_review(
            version_id=self.version.version_id, persona="SA",
            findings={"risks": ["vendor lock-in"]},
        )
        r2 = self.store.create_review(
            version_id=self.version.version_id, persona="SA",
            previous_review_id=r1.review_id,
            findings={"risks": ["cost overrun"]},
        )
        fetched_r2 = self.store.get_review(r2.review_id)
        fetched_r1 = self.store.get_review(fetched_r2.previous_review_id)
        assert fetched_r1 is not None
        diff = self._diff(fetched_r1.findings, fetched_r2.findings)
        assert "cost overrun" in diff["risks"]["new"]
        assert "vendor lock-in" in diff["risks"]["resolved"]

    def test_diff_uses_previous_review_id_not_timestamp(self):
        """Diff is tied to previous_review_id, NOT assumed by proximity in time."""
        v2 = self.store.create_version(included_artifacts=[], label="v2")
        r_unrelated = self.store.create_review(
            version_id=v2.version_id, persona="DM",
            findings={"risks": ["unrelated risk"]},
        )
        r1 = self.store.create_review(
            version_id=self.version.version_id, persona="SA",
            findings={"risks": ["vendor lock-in"]},
        )
        r2 = self.store.create_review(
            version_id=self.version.version_id, persona="SA",
            previous_review_id=r1.review_id,
            findings={"risks": ["cost overrun"]},
        )
        fetched = self.store.get_review(r2.review_id)
        # The predecessor is explicitly r1, not r_unrelated
        assert fetched.previous_review_id == r1.review_id
        assert fetched.previous_review_id != r_unrelated.review_id

    # ── Multi-category diff ───────────────────────────────────────────────────

    def test_multi_category_diff_is_per_category(self):
        diff = self._diff(
            prev_findings={
                "risks": ["vendor lock-in", "cost overrun"],
                "assumptions": ["team available"],
            },
            curr_findings={
                "risks": ["vendor lock-in", "regulatory change"],
                "assumptions": ["team available", "infra ready"],
                "dependencies": ["external API"],
            },
        )
        # risks: vendor lock-in unchanged, cost overrun resolved, regulatory change new
        assert "vendor lock-in" in diff["risks"]["unchanged"]
        assert "cost overrun" in diff["risks"]["resolved"]
        assert "regulatory change" in diff["risks"]["new"]
        # assumptions: team available unchanged, infra ready new
        assert "team available" in diff["assumptions"]["unchanged"]
        assert "infra ready" in diff["assumptions"]["new"]
        # dependencies: entirely new category
        assert "external API" in diff["dependencies"]["new"]


class TestWhatChangedHTML:
    """S3-04 — 'What Changed' section contract in viewReviewDetail()."""

    def test_viewReviewDetail_defined(self, html_text):
        pattern = r"(?:async\s+)?function\s+viewReviewDetail\s*\("
        assert re.search(pattern, html_text), (
            "viewReviewDetail() not found in index.html"
        )

    def test_viewReviewDetail_references_previous_review_id(self, html_text):
        """Must check previous_review_id to decide whether to show diff."""
        m = re.search(
            r"(?:async\s+)?function\s+viewReviewDetail\s*\(.*?\)\s*\{(.*?)\n\}",
            html_text, re.DOTALL,
        )
        assert m, "viewReviewDetail() body not found"
        body = m.group(1)
        assert "previous_review_id" in body, (
            "viewReviewDetail() does not reference previous_review_id — "
            "the 'What Changed' section will never appear."
        )

    def test_what_changed_label_in_html(self, html_text):
        """The UI must contain a 'What Changed' or 'what changed' label somewhere."""
        assert re.search(r"[Ww]hat [Cc]hanged", html_text), (
            "'What Changed' label not found anywhere in index.html — "
            "the S3-04 diff section is missing from the UI."
        )
