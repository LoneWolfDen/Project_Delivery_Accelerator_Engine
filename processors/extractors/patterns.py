"""Pattern definitions for extracting structured intelligence from text.

These patterns power the files-only (no AI) extraction mode.
They detect risks, assumptions, dependencies, constraints, resources,
and action items using keyword + structure heuristics.
"""

import re
from typing import List, Tuple

# ──────────────────────────────────────────────────────────────
# Risk patterns
# ──────────────────────────────────────────────────────────────

RISK_HEADING_KEYWORDS = [
    "risk", "risks", "risk register", "risk assessment", "concerns",
    "threats", "issues", "blockers", "impediments",
]

RISK_INLINE_PATTERNS = [
    re.compile(r"(?:risk|concern|threat|issue|blocker|impediment)\s*[:–-]\s*(.+)", re.IGNORECASE),
    re.compile(r"[-*•]\s*(?:risk|concern|issue)\s*[:–-]?\s*(.+)", re.IGNORECASE),
    re.compile(r"(?:there is a|we face|significant|critical|high)\s+risk\s+(?:of|that)\s+(.+)", re.IGNORECASE),
    re.compile(r"(?:key person|single point of failure|vendor lock-in|skill gap|timeline slip)", re.IGNORECASE),
]

# ──────────────────────────────────────────────────────────────
# Assumption patterns
# ──────────────────────────────────────────────────────────────

ASSUMPTION_HEADING_KEYWORDS = [
    "assumption", "assumptions", "assumed", "prerequisites",
]

ASSUMPTION_INLINE_PATTERNS = [
    re.compile(r"(?:assumption|assumed|prerequisite)\s*[:–-]\s*(.+)", re.IGNORECASE),
    re.compile(r"[-*•]\s*(?:assumes?|assuming|prerequisite)\s*[:–-]?\s*(.+)", re.IGNORECASE),
    re.compile(r"(?:we assume|it is assumed|assuming that)\s+(.+)", re.IGNORECASE),
]

# ──────────────────────────────────────────────────────────────
# Dependency patterns
# ──────────────────────────────────────────────────────────────

DEPENDENCY_HEADING_KEYWORDS = [
    "dependency", "dependencies", "dependent on", "requires",
    "prerequisites", "blockers", "upstream", "downstream",
]

DEPENDENCY_INLINE_PATTERNS = [
    re.compile(r"(?:depends? on|dependent on|requires|blocked by|waiting for)\s+(.+)", re.IGNORECASE),
    re.compile(r"[-*•]\s*(?:dependency|requires|blocked by)\s*[:–-]?\s*(.+)", re.IGNORECASE),
    re.compile(r"(?:must be completed before|prerequisite for|upstream)\s*[:–-]?\s*(.+)", re.IGNORECASE),
]

# ──────────────────────────────────────────────────────────────
# Constraint patterns
# ──────────────────────────────────────────────────────────────

CONSTRAINT_HEADING_KEYWORDS = [
    "constraint", "constraints", "limitations", "restrictions",
    "compliance", "regulatory", "non-negotiable",
]

CONSTRAINT_INLINE_PATTERNS = [
    re.compile(r"(?:constraint|limitation|restriction|compliance|regulatory|must not|cannot)\s*[:–-]?\s*(.+)", re.IGNORECASE),
    re.compile(r"[-*•]\s*(?:constraint|cannot|must not|no exceptions?)\s*[:–-]?\s*(.+)", re.IGNORECASE),
    re.compile(r"(?:SLA|uptime|availability)\s+(?:requires?|of)\s+(.+)", re.IGNORECASE),
    re.compile(r"(?:HIPAA|PCI-DSS|SOC2|GDPR|PCI|SOX)", re.IGNORECASE),
]

# ──────────────────────────────────────────────────────────────
# Resource patterns
# ──────────────────────────────────────────────────────────────

RESOURCE_HEADING_KEYWORDS = [
    "resource", "resources", "team", "staffing", "capacity",
    "resource requirements", "resource plan", "allocation",
]

RESOURCE_INLINE_PATTERNS = [
    re.compile(r"(\d+)\s*x?\s*(senior|junior|mid|lead)?\s*(engineer|developer|architect|manager|specialist|consultant|analyst)", re.IGNORECASE),
    re.compile(r"(?:team of|need|require)\s+(\d+)\s+(\w+)", re.IGNORECASE),
    re.compile(r"(?:full[- ]time|part[- ]time|contractor|FTE)", re.IGNORECASE),
]

# ──────────────────────────────────────────────────────────────
# Action item patterns
# ──────────────────────────────────────────────────────────────

ACTION_HEADING_KEYWORDS = [
    "action item", "action items", "actions", "next steps",
    "follow-up", "follow up", "todo", "to-do",
]

ACTION_INLINE_PATTERNS = [
    re.compile(r"[-*•]\s*([A-Z][A-Za-z\s.]+?)\s*[:–-]\s*(.+)", re.IGNORECASE),
    re.compile(r"(?:action|todo|follow[- ]?up)\s*[:–-]\s*(.+)", re.IGNORECASE),
]

# ──────────────────────────────────────────────────────────────
# Scope patterns
# ──────────────────────────────────────────────────────────────

SCOPE_HEADING_KEYWORDS = [
    "scope", "scope of work", "objectives", "deliverables",
    "executive summary", "overview", "goals",
]


def matches_heading(heading: str, keywords: List[str]) -> bool:
    """Check if a section heading matches any keyword."""
    heading_lower = heading.lower().strip()
    return any(kw in heading_lower for kw in keywords)


def extract_by_patterns(text: str, patterns: List[re.Pattern]) -> List[str]:
    """Extract matches from text using a list of regex patterns.

    Returns deduplicated, cleaned match strings.
    """
    results: List[str] = []
    for pattern in patterns:
        for match in pattern.finditer(text):
            # Use the last non-None group
            groups = [g for g in match.groups() if g]
            if groups:
                value = groups[-1].strip().rstrip(".,;")
                if value and len(value) > 5 and value not in results:
                    results.append(value)
            else:
                # Full match for patterns without groups
                value = match.group(0).strip().rstrip(".,;")
                if value and len(value) > 5 and value not in results:
                    results.append(value)
    return results


def extract_bullet_items(text: str) -> List[str]:
    """Extract bullet-pointed items from text."""
    bullet_re = re.compile(r"^\s*[-*•]\s+(.+)$", re.MULTILINE)
    return [m.group(1).strip() for m in bullet_re.finditer(text) if len(m.group(1).strip()) > 5]


def extract_numbered_items(text: str) -> List[str]:
    """Extract numbered list items from text."""
    numbered_re = re.compile(r"^\s*\d+[.)]\s+(.+)$", re.MULTILINE)
    return [m.group(1).strip() for m in numbered_re.finditer(text) if len(m.group(1).strip()) > 5]
