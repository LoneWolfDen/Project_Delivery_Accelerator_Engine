"""Sprint 9 Regression Pack — Health Signal, Pinned Insights, Project Memory Score.

All tests are static-analysis of the v2 JS / CSS / HTML files.
v1 (static/index.html) is NOT read — confirmed untouched by these tests.

Feature map
-----------
F1  HealthSignal       — RAG status (summary_health.js)
F2  PinnedInsights     — Pinned items with localStorage (bookmarks.js)
F3  ProjectMemoryScore — Maturity score + progress bar (metrics.js)
F4  CSS classes        — components.css additions
F5  accordion.js wiring — health badge + pin button in version headers
F6  dashboard_v2.html wiring — script tags + slot divs + render calls
F7  v1 untouched       — static/index.html not modified

Section index
─────────────
A  F1 – HealthSignal (summary_health.js)
B  F2 – PinnedInsights (bookmarks.js)
C  F3 – ProjectMemoryScore (metrics.js)
D  F4 – CSS classes (components.css)
E  F5 – accordion.js wiring
F  F6 – dashboard_v2.html wiring
G  F7 – v1 untouched
"""

from __future__ import annotations

from pathlib import Path

import pytest

# ── File paths ────────────────────────────────────────────────────────────────
BASE = Path(__file__).parent.parent

HEALTH_JS    = BASE / "static" / "v2" / "js" / "summary_health.js"
BOOKMARKS_JS = BASE / "static" / "v2" / "js" / "bookmarks.js"
METRICS_JS   = BASE / "static" / "v2" / "js" / "metrics.js"
COMPONENTS_CSS = BASE / "static" / "v2" / "css" / "components.css"
ACCORDION_JS = BASE / "static" / "v2" / "js" / "accordion.js"
DASHBOARD_V2 = BASE / "static" / "v2" / "dashboard_v2.html"
INDEX_HTML   = BASE / "static" / "index.html"



# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def health_js() -> str:
    return HEALTH_JS.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def bookmarks_js() -> str:
    return BOOKMARKS_JS.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def metrics_js() -> str:
    return METRICS_JS.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def components_css() -> str:
    return COMPONENTS_CSS.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def accordion_js() -> str:
    return ACCORDION_JS.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def dashboard_v2() -> str:
    return DASHBOARD_V2.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def index_html() -> str:
    return INDEX_HTML.read_text(encoding="utf-8")



# ─────────────────────────────────────────────────────────────────────────────
# A  F1 – HealthSignal (summary_health.js)
# ─────────────────────────────────────────────────────────────────────────────

class TestF1HealthSignal:
    def test_file_exists(self):
        assert HEALTH_JS.exists(), "summary_health.js must exist"

    def test_module_name_defined(self, health_js):
        assert "const HealthSignal" in health_js

    def test_window_export(self, health_js):
        assert "window.HealthSignal = HealthSignal" in health_js

    def test_compute_health_function(self, health_js):
        assert "function computeHealth(" in health_js

    def test_render_badge_function(self, health_js):
        assert "function renderBadge(" in health_js

    def test_render_version_badge_function(self, health_js):
        assert "function renderVersionBadge(" in health_js

    def test_render_card_function(self, health_js):
        assert "function renderCard(" in health_js

    def test_update_function(self, health_js):
        assert "function update(" in health_js

    def test_mount_function(self, health_js):
        assert "function mount(" in health_js

    def test_three_levels_red(self, health_js):
        assert "LEVELS.RED" in health_js or "'red'" in health_js

    def test_three_levels_amber(self, health_js):
        assert "LEVELS.AMBER" in health_js or "'amber'" in health_js

    def test_three_levels_green(self, health_js):
        assert "LEVELS.GREEN" in health_js or "'green'" in health_js

    def test_high_risk_threshold_defined(self, health_js):
        assert "HIGH_RISK_THRESHOLD" in health_js

    def test_med_risk_threshold_defined(self, health_js):
        assert "MED_RISK_THRESHOLD" in health_js

    def test_badge_class_green(self, health_js):
        assert "health-badge--green" in health_js

    def test_badge_class_amber(self, health_js):
        assert "health-badge--amber" in health_js

    def test_badge_class_red(self, health_js):
        assert "health-badge--red" in health_js

    def test_uses_risks_identified(self, health_js):
        assert "risks_identified" in health_js

    def test_uses_gaps_identified(self, health_js):
        assert "gaps_identified" in health_js

    def test_dom_target_id(self, health_js):
        assert "v2-health-badge" in health_js

    def test_appstate_subscribe(self, health_js):
        assert "state.subscribe(" in health_js

    def test_auto_mount_on_dom_ready(self, health_js):
        assert "DOMContentLoaded" in health_js

    def test_no_external_libraries(self, health_js):
        assert "import " not in health_js
        assert "require(" not in health_js



# ─────────────────────────────────────────────────────────────────────────────
# B  F2 – PinnedInsights (bookmarks.js)
# ─────────────────────────────────────────────────────────────────────────────

class TestF2PinnedInsights:
    def test_file_exists(self):
        assert BOOKMARKS_JS.exists(), "bookmarks.js must exist"

    def test_module_name_defined(self, bookmarks_js):
        assert "const PinnedInsights" in bookmarks_js

    def test_window_export(self, bookmarks_js):
        assert "window.PinnedInsights = PinnedInsights" in bookmarks_js

    def test_storage_key_defined(self, bookmarks_js):
        assert "pdae_v2_pins" in bookmarks_js

    def test_storage_key_constant(self, bookmarks_js):
        assert "STORAGE_KEY" in bookmarks_js

    def test_max_pins_constant(self, bookmarks_js):
        assert "MAX_PINS" in bookmarks_js

    def test_get_pins_function(self, bookmarks_js):
        assert "function getPins(" in bookmarks_js

    def test_is_pinned_function(self, bookmarks_js):
        assert "function isPinned(" in bookmarks_js

    def test_toggle_function(self, bookmarks_js):
        assert "function toggle(" in bookmarks_js

    def test_unpin_function(self, bookmarks_js):
        assert "function unpin(" in bookmarks_js

    def test_clear_project_function(self, bookmarks_js):
        assert "function clearProject(" in bookmarks_js

    def test_on_change_function(self, bookmarks_js):
        assert "function onChange(" in bookmarks_js

    def test_render_pin_button_function(self, bookmarks_js):
        assert "function renderPinButton(" in bookmarks_js

    def test_render_section_function(self, bookmarks_js):
        assert "function renderSection(" in bookmarks_js

    def test_update_section_function(self, bookmarks_js):
        assert "function updateSection(" in bookmarks_js

    def test_pin_click_handler(self, bookmarks_js):
        assert "function onPinClick(" in bookmarks_js

    def test_remove_click_handler(self, bookmarks_js):
        assert "function onRemoveClick(" in bookmarks_js

    def test_clear_click_handler(self, bookmarks_js):
        assert "function onClearClick(" in bookmarks_js

    def test_supports_version_type(self, bookmarks_js):
        assert "'version'" in bookmarks_js

    def test_supports_review_type(self, bookmarks_js):
        assert "'review'" in bookmarks_js

    def test_supports_risk_type(self, bookmarks_js):
        assert "'risk'" in bookmarks_js

    def test_localstorage_get_item(self, bookmarks_js):
        assert "localStorage.getItem(" in bookmarks_js

    def test_localstorage_set_item(self, bookmarks_js):
        assert "localStorage.setItem(" in bookmarks_js

    def test_dom_target_pinned_section(self, bookmarks_js):
        assert "v2-pinned-section" in bookmarks_js

    def test_pin_btn_class(self, bookmarks_js):
        assert "pin-btn" in bookmarks_js

    def test_pin_btn_active_class(self, bookmarks_js):
        assert "pin-btn--active" in bookmarks_js

    def test_pinned_item_class(self, bookmarks_js):
        assert "pinned-item" in bookmarks_js

    def test_mount_function(self, bookmarks_js):
        assert "function mount(" in bookmarks_js

    def test_auto_mount_on_dom_ready(self, bookmarks_js):
        assert "DOMContentLoaded" in bookmarks_js

    def test_does_not_use_old_storage_key(self, bookmarks_js):
        # Must not clobber existing localStorage keys
        assert "pdae_current_project_id" not in bookmarks_js

    def test_no_external_libraries(self, bookmarks_js):
        assert "import " not in bookmarks_js
        assert "require(" not in bookmarks_js

    def test_fail_safe_parse_error(self, bookmarks_js):
        # _loadAll must catch JSON parse errors
        assert "catch" in bookmarks_js



# ─────────────────────────────────────────────────────────────────────────────
# C  F3 – ProjectMemoryScore (metrics.js)
# ─────────────────────────────────────────────────────────────────────────────

class TestF3ProjectMemoryScore:
    def test_file_exists(self):
        assert METRICS_JS.exists(), "metrics.js must exist"

    def test_module_name_defined(self, metrics_js):
        assert "const ProjectMemoryScore" in metrics_js

    def test_window_export(self, metrics_js):
        assert "window.ProjectMemoryScore = ProjectMemoryScore" in metrics_js

    def test_compute_function(self, metrics_js):
        assert "function compute(" in metrics_js

    def test_render_function(self, metrics_js):
        assert "function render(" in metrics_js

    def test_update_function(self, metrics_js):
        assert "function update(" in metrics_js

    def test_mount_function(self, metrics_js):
        assert "function mount(" in metrics_js

    def test_weight_versions_defined(self, metrics_js):
        assert "WEIGHT_VERSIONS" in metrics_js

    def test_weight_reviews_defined(self, metrics_js):
        assert "WEIGHT_REVIEWS" in metrics_js

    def test_weight_risks_defined(self, metrics_js):
        assert "WEIGHT_RISKS" in metrics_js

    def test_weight_depth_defined(self, metrics_js):
        assert "WEIGHT_DEPTH" in metrics_js

    def test_weights_sum_to_one(self, metrics_js):
        # Extract numeric weight values and verify they sum to 1.0
        import re
        vals = re.findall(r'WEIGHT_\w+\s*=\s*([\d.]+)', metrics_js)
        assert vals, "Weight constants must be numeric"
        total = sum(float(v) for v in vals)
        assert abs(total - 1.0) < 1e-9, f"Weights must sum to 1.0, got {total}"

    def test_version_max_defined(self, metrics_js):
        assert "VERSION_MAX" in metrics_js

    def test_review_max_defined(self, metrics_js):
        assert "REVIEW_MAX" in metrics_js

    def test_risk_max_defined(self, metrics_js):
        assert "RISK_MAX" in metrics_js

    def test_depth_max_defined(self, metrics_js):
        assert "DEPTH_MAX" in metrics_js

    def test_bands_defined(self, metrics_js):
        assert "const BANDS" in metrics_js

    def test_band_expert(self, metrics_js):
        assert "Expert" in metrics_js

    def test_band_advanced(self, metrics_js):
        assert "Advanced" in metrics_js

    def test_band_maturing(self, metrics_js):
        assert "Maturing" in metrics_js

    def test_band_developing(self, metrics_js):
        assert "Developing" in metrics_js

    def test_band_early_stage(self, metrics_js):
        assert "Early Stage" in metrics_js

    def test_label_format(self, metrics_js):
        assert "Project Learning Maturity" in metrics_js

    def test_progress_bar_rendered(self, metrics_js):
        assert "memory-bar" in metrics_js

    def test_segmented_bar_versions_seg(self, metrics_js):
        assert "seg--versions" in metrics_js

    def test_segmented_bar_reviews_seg(self, metrics_js):
        assert "seg--reviews" in metrics_js

    def test_segmented_bar_risks_seg(self, metrics_js):
        assert "seg--risks" in metrics_js

    def test_segmented_bar_depth_seg(self, metrics_js):
        assert "seg--depth" in metrics_js

    def test_dom_target_id(self, metrics_js):
        assert "v2-memory-score" in metrics_js

    def test_appstate_subscribe_metrics(self, metrics_js):
        assert "'metrics'" in metrics_js

    def test_appstate_subscribe_versions(self, metrics_js):
        assert "'versions'" in metrics_js

    def test_auto_mount_on_dom_ready(self, metrics_js):
        assert "DOMContentLoaded" in metrics_js

    def test_score_clamped(self, metrics_js):
        assert "_clamp(" in metrics_js or "Math.min" in metrics_js

    def test_score_rounded(self, metrics_js):
        assert "Math.round(" in metrics_js

    def test_no_external_libraries(self, metrics_js):
        assert "import " not in metrics_js
        assert "require(" not in metrics_js



# ─────────────────────────────────────────────────────────────────────────────
# D  F4 – CSS classes (components.css)
# ─────────────────────────────────────────────────────────────────────────────

class TestF4CSSClasses:
    # Health badge
    def test_health_badge_class(self, components_css):
        assert ".health-badge" in components_css

    def test_health_badge_green(self, components_css):
        assert ".health-badge--green" in components_css

    def test_health_badge_amber(self, components_css):
        assert ".health-badge--amber" in components_css

    def test_health_badge_red(self, components_css):
        assert ".health-badge--red" in components_css

    def test_health_card_class(self, components_css):
        assert ".health-card" in components_css

    def test_health_card_body(self, components_css):
        assert ".health-card-body" in components_css

    def test_health_card_value(self, components_css):
        assert ".health-card-value" in components_css

    # Pin button
    def test_pin_btn_class(self, components_css):
        assert ".pin-btn" in components_css

    def test_pin_btn_active_class(self, components_css):
        assert ".pin-btn--active" in components_css

    # Pinned section
    def test_pinned_section_class(self, components_css):
        assert ".pinned-section" in components_css

    def test_pinned_section_header(self, components_css):
        assert ".pinned-section-header" in components_css

    def test_pinned_section_title(self, components_css):
        assert ".pinned-section-title" in components_css

    def test_pinned_item_class(self, components_css):
        assert ".pinned-item" in components_css

    def test_pinned_item_label(self, components_css):
        assert ".pinned-item-label" in components_css

    def test_pin_remove_btn(self, components_css):
        assert ".pin-remove-btn" in components_css

    def test_pin_type_version(self, components_css):
        assert ".pin-type--version" in components_css

    def test_pin_type_review(self, components_css):
        assert ".pin-type--review" in components_css

    def test_pin_type_risk(self, components_css):
        assert ".pin-type--risk" in components_css

    # Memory score
    def test_memory_score_card(self, components_css):
        assert ".memory-score-card" in components_css

    def test_memory_score_value(self, components_css):
        assert ".memory-score-value" in components_css

    def test_memory_bar(self, components_css):
        assert ".memory-bar" in components_css

    def test_memory_bar_wrap(self, components_css):
        assert ".memory-bar-wrap" in components_css

    def test_memory_seg_versions(self, components_css):
        assert ".memory-seg--versions" in components_css

    def test_memory_seg_reviews(self, components_css):
        assert ".memory-seg--reviews" in components_css

    def test_memory_seg_risks(self, components_css):
        assert ".memory-seg--risks" in components_css

    def test_memory_seg_depth(self, components_css):
        assert ".memory-seg--depth" in components_css

    def test_memory_legend(self, components_css):
        assert ".memory-legend" in components_css

    def test_memory_score_band_badge(self, components_css):
        assert ".memory-score-band-badge" in components_css

    def test_score_band_expert(self, components_css):
        assert ".score-band--expert" in components_css

    def test_score_band_maturing(self, components_css):
        assert ".score-band--maturing" in components_css

    def test_score_band_early(self, components_css):
        assert ".score-band--early" in components_css



# ─────────────────────────────────────────────────────────────────────────────
# E  F5 – accordion.js wiring
# ─────────────────────────────────────────────────────────────────────────────

class TestF5AccordionWiring:
    def test_health_signal_guard(self, accordion_js):
        # HealthSignal called defensively
        assert "window.HealthSignal" in accordion_js

    def test_render_version_badge_called(self, accordion_js):
        assert "HealthSignal.renderVersionBadge(" in accordion_js

    def test_pinned_insights_guard(self, accordion_js):
        assert "window.PinnedInsights" in accordion_js

    def test_render_pin_button_called(self, accordion_js):
        assert "PinnedInsights.renderPinButton(" in accordion_js

    def test_pin_button_type_version(self, accordion_js):
        # pin button in accordion must use 'version' type
        idx = accordion_js.index("PinnedInsights.renderPinButton(")
        snippet = accordion_js[idx: idx + 200]
        assert "'version'" in snippet

    def test_health_badge_html_in_header(self, accordion_js):
        # healthBadgeHtml variable inserted into accordion header template
        assert "healthBadgeHtml" in accordion_js

    def test_pin_btn_html_in_header(self, accordion_js):
        assert "pinBtnHtml" in accordion_js

    def test_accordion_version_id_still_present(self, accordion_js):
        # Existing content not broken
        assert "accordion-version-id" in accordion_js

    def test_accordion_meta_still_present(self, accordion_js):
        assert "accordion-meta" in accordion_js

    def test_version_detail_button_still_present(self, accordion_js):
        assert "onVersionDetailClick" in accordion_js


# ─────────────────────────────────────────────────────────────────────────────
# F  F6 – dashboard_v2.html wiring
# ─────────────────────────────────────────────────────────────────────────────

class TestF6DashboardV2Wiring:
    def test_summary_health_script_tag(self, dashboard_v2):
        assert 'src="/static/v2/js/summary_health.js"' in dashboard_v2

    def test_bookmarks_script_tag(self, dashboard_v2):
        assert 'src="/static/v2/js/bookmarks.js"' in dashboard_v2

    def test_metrics_script_tag(self, dashboard_v2):
        assert 'src="/static/v2/js/metrics.js"' in dashboard_v2

    def test_health_badge_slot_div(self, dashboard_v2):
        assert 'id="v2-health-badge"' in dashboard_v2

    def test_pinned_section_slot_div(self, dashboard_v2):
        assert 'id="v2-pinned-section"' in dashboard_v2

    def test_memory_score_slot_div(self, dashboard_v2):
        assert 'id="v2-memory-score"' in dashboard_v2

    def test_health_signal_update_call(self, dashboard_v2):
        assert "HealthSignal.update(" in dashboard_v2

    def test_memory_score_update_call(self, dashboard_v2):
        assert "ProjectMemoryScore.update(" in dashboard_v2

    def test_pinned_update_section_call(self, dashboard_v2):
        assert "PinnedInsights.updateSection(" in dashboard_v2

    def test_sprint9_scripts_after_compare(self, dashboard_v2):
        # New scripts must load after compare.js (ordering)
        idx_cmp    = dashboard_v2.index('src="/static/v2/js/compare.js"')
        idx_health = dashboard_v2.index('src="/static/v2/js/summary_health.js"')
        assert idx_cmp < idx_health

    def test_sprint9_scripts_after_search(self, dashboard_v2):
        idx_search = dashboard_v2.index('src="/static/v2/js/search.js"')
        idx_health = dashboard_v2.index('src="/static/v2/js/summary_health.js"')
        assert idx_search < idx_health

    def test_pinned_section_before_activity(self, dashboard_v2):
        # Pinned section slot appears before the activity / overview content
        idx_pinned   = dashboard_v2.index('id="v2-pinned-section"')
        idx_memory   = dashboard_v2.index('id="v2-memory-score"')
        assert idx_pinned < idx_memory

    def test_v1_compare_js_unchanged(self, dashboard_v2):
        # compare.js script tag still present (existing feature intact)
        assert 'src="/static/v2/js/compare.js"' in dashboard_v2

    def test_v1_search_js_unchanged(self, dashboard_v2):
        assert 'src="/static/v2/js/search.js"' in dashboard_v2


# ─────────────────────────────────────────────────────────────────────────────
# G  F7 – v1 untouched
# ─────────────────────────────────────────────────────────────────────────────

class TestF7V1Untouched:
    def test_summary_health_not_in_v1(self, index_html):
        assert "summary_health.js" not in index_html

    def test_bookmarks_not_in_v1(self, index_html):
        assert "bookmarks.js" not in index_html

    def test_metrics_js_not_in_v1(self, index_html):
        assert "metrics.js" not in index_html

    def test_health_signal_not_in_v1(self, index_html):
        assert "HealthSignal" not in index_html

    def test_pinned_insights_not_in_v1(self, index_html):
        assert "PinnedInsights" not in index_html

    def test_project_memory_score_not_in_v1(self, index_html):
        assert "ProjectMemoryScore" not in index_html

    def test_v2_health_badge_id_not_in_v1(self, index_html):
        assert "v2-health-badge" not in index_html

    def test_v2_memory_score_id_not_in_v1(self, index_html):
        assert "v2-memory-score" not in index_html

    def test_v2_pinned_section_id_not_in_v1(self, index_html):
        assert "v2-pinned-section" not in index_html

    def test_pdae_v2_pins_not_in_v1(self, index_html):
        assert "pdae_v2_pins" not in index_html
