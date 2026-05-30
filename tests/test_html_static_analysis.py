"""Static analysis regression tests for static/index.html.

WHY THIS FILE EXISTS
--------------------
PR #62 introduced a <script> tag inside a JS template literal string:

    const runCard = `...
      <script>
        if(!state._injectedQuestions) ...
      </script>
    `;                     ← template literal closes here

The browser HTML parser sees the first </script> and terminates the
enclosing <script> block immediately.  Everything after that line is
rendered as raw HTML instead of executed as JS, producing:

    Uncaught SyntaxError: Unexpected end of input
    ReferenceError: viewReviews is not defined

This class of bug is invisible to Python unit tests that only test the
backend.  These tests read index.html as text and apply structural rules
that would have failed on the bad commit and pass on the fixed one.

RULES TESTED
------------
1. No <script> tag appears inside a JS template literal string.
2. Every top-level <script> block is properly closed with </script>.
3. The file is UTF-8 decodable without errors.
4. All JS view-function names referenced in the render() dispatch table
   are actually defined in the file (catches ReferenceError at load time).
5. Template literals that produce innerHTML must not embed raw </script>
   close tags (the complementary half of rule 1).
"""

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

HTML_PATH = Path(__file__).parent.parent / "static" / "index.html"


@pytest.fixture(scope="module")
def html_text():
    """Read index.html once for all tests in this module."""
    return HTML_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def script_blocks(html_text):
    """Extract the JS source from every top-level <script>…</script> block.

    Returns a list of (start_line, js_source) tuples.
    """
    blocks = []
    # Use a non-greedy match; DOTALL so . spans newlines.
    for m in re.finditer(r"<script[^>]*>(.*?)</script>", html_text, re.DOTALL | re.IGNORECASE):
        # Determine line number of the opening tag
        start_line = html_text[: m.start()].count("\n") + 1
        blocks.append((start_line, m.group(1)))
    return blocks


# ── Rule 1 & 5: no <script> / </script> inside template literals ─────────────

class TestNoScriptTagsInsideTemplateLiterals:
    """The exact class of bug introduced in PR #62."""

    def _find_template_literal_contents(self, js_source: str):
        """Yield all content strings found between backtick delimiters.

        This is a conservative approximation: it finds stretches of text
        between unescaped backticks.  False positives (nested backticks in
        regex literals etc.) are acceptable — the rule is a safety net.
        """
        # Split on unescaped backtick (not preceded by backslash)
        parts = re.split(r"(?<!\\)`", js_source)
        # Odd-indexed parts are inside backticks (0=before first, 1=first literal, ...)
        for i, part in enumerate(parts):
            if i % 2 == 1:  # inside a template literal
                yield part

    def test_no_script_open_tag_in_any_template_literal(self, script_blocks):
        """<script inside a template literal kills the enclosing JS block."""
        violations = []
        for start_line, js in script_blocks:
            for literal in self._find_template_literal_contents(js):
                # Match <script with optional attributes, case-insensitive
                matches = list(re.finditer(r"<script[\s>]", literal, re.IGNORECASE))
                if matches:
                    # Compute approximate line number within the file
                    lines_before = js[: js.index(literal)].count("\n") if literal in js else 0
                    approx_line = start_line + lines_before
                    violations.append(
                        f"<script> tag found inside a template literal "
                        f"(approx. file line {approx_line})"
                    )
        assert not violations, (
            "FAIL — <script> tag(s) found inside JS template literals.\n"
            "This causes the browser HTML parser to close the outer <script> "
            "block early, breaking ALL subsequent JS.\n"
            "Violations:\n" + "\n".join(f"  • {v}" for v in violations)
        )

    def test_no_script_close_tag_in_any_template_literal(self, script_blocks):
        """</script> inside a template literal is equally fatal."""
        violations = []
        for start_line, js in script_blocks:
            for literal in self._find_template_literal_contents(js):
                matches = list(re.finditer(r"</script\s*>", literal, re.IGNORECASE))
                if matches:
                    violations.append(
                        f"</script> tag found inside a template literal "
                        f"starting near file line {start_line}"
                    )
        assert not violations, (
            "FAIL — </script> tag(s) found inside JS template literals.\n"
            "Violations:\n" + "\n".join(f"  • {v}" for v in violations)
        )

    def test_reproduces_pr62_bug_pattern(self):
        """Canary: confirm this test WOULD fail on the exact bad code from PR #62.

        Constructs the bad string in Python and verifies our detector flags it.
        The test itself must pass (the detector works correctly).
        """
        bad_js = r"""
const runCard=`
  <div class="card">
    <script>
      if(!state._injectedQuestions)state._injectedQuestions=[];
      setTimeout(()=>_renderInjectedQuestions(),0);
    </script>
  </div>
`;
"""
        # Replicate the detection logic from the test above
        parts = re.split(r"(?<!\\)`", bad_js)
        found = False
        for i, part in enumerate(parts):
            if i % 2 == 1:
                if re.search(r"<script[\s>]", part, re.IGNORECASE):
                    found = True
        assert found, (
            "Canary failure: the detector did NOT flag the PR #62 bad pattern. "
            "The detection logic itself is broken — fix the test."
        )

    def test_fixed_code_is_clean(self):
        """Canary: confirm the fixed version is NOT flagged by our detector."""
        fixed_js = r"""
const runCard=`
  <div class="card">
    <div id="deepDiveResult" class="mt"></div>
    <div id="reviewResult" class="mt"></div>
  </div>
`;
"""
        parts = re.split(r"(?<!\\)`", fixed_js)
        found = False
        for i, part in enumerate(parts):
            if i % 2 == 1:
                if re.search(r"<script[\s>]", part, re.IGNORECASE):
                    found = True
        assert not found, (
            "Canary failure: the detector flagged clean code as a violation."
        )


# ── Rule 2: every <script> block is properly closed ──────────────────────────

class TestScriptBlocksAreProperlyClosed:

    def test_script_open_and_close_tags_are_balanced(self, html_text):
        """Count of <script> must equal count of </script> in the file."""
        opens = len(re.findall(r"<script[>\s]", html_text, re.IGNORECASE))
        closes = len(re.findall(r"</script\s*>", html_text, re.IGNORECASE))
        assert opens == closes, (
            f"Unbalanced <script> tags: {opens} opening, {closes} closing. "
            "A mismatch means the HTML parser will misinterpret block boundaries."
        )

    def test_no_script_block_is_empty_of_source(self, script_blocks):
        """Every <script>…</script> block must contain at least one non-whitespace char."""
        empty = [
            f"block at line {lineno}"
            for lineno, js in script_blocks
            if not js.strip()
        ]
        assert not empty, (
            "Empty <script> blocks found (probably a parser split artefact): "
            + ", ".join(empty)
        )


# ── Rule 3: file encoding ─────────────────────────────────────────────────────

class TestFileEncoding:

    def test_utf8_decodable(self):
        """index.html must be valid UTF-8."""
        try:
            HTML_PATH.read_bytes().decode("utf-8")
        except UnicodeDecodeError as e:
            pytest.fail(f"index.html is not valid UTF-8: {e}")

    def test_no_null_bytes(self, html_text):
        assert "\x00" not in html_text, "index.html contains null bytes."


# ── Rule 4: view functions referenced in render() are defined ─────────────────

class TestViewFunctionsAreDefined:
    """Catches ReferenceError: viewXxx is not defined at runtime."""

    # Names extracted from the render() dispatch table in index.html
    REQUIRED_VIEW_FUNCTIONS = [
        "viewDashboard",
        "viewIngest",
        "viewIntelligence",
        "viewVersions",
        "viewReviews",
        "viewDiagrams",
        "viewPhases",
        "viewPresales",
        "viewSettings",
        "viewAdmin",
    ]

    def test_all_dispatch_view_functions_are_defined(self, html_text):
        """Every function in the render() dispatch table must be defined."""
        missing = []
        for fn in self.REQUIRED_VIEW_FUNCTIONS:
            # Match: async function viewXxx( or function viewXxx(
            pattern = rf"(?:async\s+)?function\s+{re.escape(fn)}\s*\("
            if not re.search(pattern, html_text):
                missing.append(fn)
        assert not missing, (
            "The following view functions are referenced in render() but NOT "
            "defined in index.html:\n"
            + "\n".join(f"  • {fn}" for fn in missing)
            + "\nThis causes ReferenceError at page load."
        )

    def test_render_dispatch_table_matches_required_set(self, html_text):
        """The dispatch table in render() must contain all required view functions."""
        # Find the views={...} object in render()
        m = re.search(r"const\s+views\s*=\s*\{([^}]+)\}", html_text)
        assert m, "Could not locate 'const views = {...}' in index.html"
        table_src = m.group(1)
        defined_in_table = re.findall(r"\b(view\w+)\b", table_src)
        for fn in self.REQUIRED_VIEW_FUNCTIONS:
            assert fn in defined_in_table, (
                f"{fn} is in REQUIRED_VIEW_FUNCTIONS but missing from the "
                f"render() dispatch table."
            )


# ── Rule: key S2 helper functions are defined ─────────────────────────────────

class TestS2HelperFunctionsDefined:
    """Ensures helpers introduced in Sprint 2 are present and callable."""

    REQUIRED_HELPERS = [
        "_renderInjectedQuestions",
        "_removeInjectedQuestion",
        "_getBaselinePrompt",
        "addSelectedToPrompt",
        "runReview",
        "runDeepDive",
    ]

    def test_s2_helpers_are_defined(self, html_text):
        missing = []
        for fn in self.REQUIRED_HELPERS:
            pattern = rf"(?:async\s+)?function\s+{re.escape(fn)}\s*\("
            if not re.search(pattern, html_text):
                missing.append(fn)
        assert not missing, (
            "Sprint 2 helper function(s) missing from index.html:\n"
            + "\n".join(f"  • {fn}" for fn in missing)
        )

    def test_userNotes_textarea_exists_in_source(self, html_text):
        """The userNotes textarea (Section 3 of prompt builder) must exist."""
        assert 'id="userNotes"' in html_text, (
            'Prompt builder Section 3 textarea (id="userNotes") not found in index.html'
        )

    def test_injectedQuestions_container_exists_in_source(self, html_text):
        """The injected questions container (Section 2) must exist."""
        assert 'id="injectedQuestions"' in html_text, (
            'Prompt builder Section 2 container (id="injectedQuestions") '
            "not found in index.html"
        )

    def test_customPrompt_textarea_is_removed(self, html_text):
        """The old single customPrompt textarea must be gone (replaced by builder)."""
        assert 'id="customPrompt"' not in html_text, (
            'Old id="customPrompt" textarea still present in index.html. '
            "It should have been replaced by the three-section prompt builder (S2-01)."
        )
