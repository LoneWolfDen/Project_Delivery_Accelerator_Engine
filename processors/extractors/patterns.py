"""Pattern definitions for extracting structured intelligence from text.

These patterns power the files-only (no AI) extraction mode.
They detect risks, assumptions, dependencies, constraints, resources,
and action items using keyword + structure heuristics.

Design principles:
- Prefer precision over recall (fewer false positives)
- Minimum match length to avoid fragment noise
- Exclude markdown table syntax (|, ---)
- Patterns are ordered most-specific-first
"""

import re
from typing import List

# ──────────────────────────────────────────────────────────────
# Content filters (applied before extraction)
# ──────────────────────────────────────────────────────────────

# Lines that are markdown table structure (not content)
TABLE_SEPARATOR = re.compile(r"^\s*\|[-:|\s]+\|\s*$")
TABLE_HEADER_LINE = re.compile(r"^\s*\|.*\|\s*$")

# Minimum quality thresholds
MIN_EXTRACTION_LENGTH = 15  # Items shorter than this are too vague
MAX_EXTRACTION_LENGTH = 300  # Items longer than this are likely full paragraphs


def is_noise_line(text: str) -> bool:
    """Check if a line is structural noise (table separators, etc.)."""
    stripped = text.strip()
    if TABLE_SEPARATOR.match(stripped):
        return True
    # Pure pipe-separated header with no useful content
    if stripped.startswith("|") and stripped.endswith("|") and "---" in stripped:
        return True
    # Too short to be meaningful
    if len(stripped) < MIN_EXTRACTION_LENGTH:
        return True
    return False


def clean_extraction(text: str) -> str:
    """Clean an extracted item: remove table pipes, trim, normalise."""
    # Strip leading/trailing pipes and whitespace
    cleaned = text.strip().strip("|").strip()
    # Remove leading markdown bold markers
    cleaned = re.sub(r"^\*\*(.+?)\*\*\s*", r"\1 ", cleaned)
    # Collapse multiple spaces
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    # Remove trailing punctuation noise
    cleaned = cleaned.rstrip(".,;:|")
    return cleaned.strip()


# ──────────────────────────────────────────────────────────────
# Markdown table parser
# ──────────────────────────────────────────────────────────────


def extract_table_rows(text: str) -> List[List[str]]:
    """Extract rows from a markdown table as lists of cell values.

    Filters out header separators and returns data rows only.
    """
    rows: List[List[str]] = []
    lines = text.splitlines()
    header_found = False

    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        if TABLE_SEPARATOR.match(stripped):
            header_found = True
            continue
        # Skip the header row (first row before separator)
        if not header_found:
            continue
        # Parse data row
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if cells and any(c for c in cells):
            rows.append(cells)

    return rows


# ──────────────────────────────────────────────────────────────
# Risk patterns
# ──────────────────────────────────────────────────────────────

RISK_HEADING_KEYWORDS = [
    "risk", "risks", "risk register", "risk assessment", "concerns",
    "threats", "issues", "blockers", "impediments",
]

RISK_INLINE_PATTERNS = [
    # Explicit risk declarations
    re.compile(
        r"(?:risk|concern|threat|issue|blocker)\s*[:–-]\s*(.{15,200})",
        re.IGNORECASE,
    ),
    # Bullet items mentioning risk
    re.compile(
        r"[-*•]\s*(?:risk|concern|issue)\s*[:–-]?\s*(.{15,200})",
        re.IGNORECASE,
    ),
    # Narrative risk statements
    re.compile(
        r"(?:there is a|we face a?|significant|critical|high)\s+risk\s+(?:of|that)\s+(.{15,200})",
        re.IGNORECASE,
    ),
    # Common risk phrases with context
    re.compile(
        r"(key[- ]person dependency.{0,80}|single point of failure.{0,80}|"
        r"vendor lock-in.{0,80}|skill gap.{0,80}|timeline.{0,40}slip.{0,80})",
        re.IGNORECASE,
    ),
]

# ──────────────────────────────────────────────────────────────
# Assumption patterns
# ──────────────────────────────────────────────────────────────

ASSUMPTION_HEADING_KEYWORDS = [
    "assumption", "assumptions", "assumed", "prerequisites",
]

ASSUMPTION_INLINE_PATTERNS = [
    # Explicit assumption declarations
    re.compile(
        r"(?:assumption|assumed|prerequisite)\s*[:–-]\s*(.{15,200})",
        re.IGNORECASE,
    ),
    # Bullet items with assumption keywords
    re.compile(
        r"[-*•]\s*(?:assumes?|assuming|prerequisite)\s*[:–-]?\s*(.{15,200})",
        re.IGNORECASE,
    ),
    # Narrative assumption phrases
    re.compile(
        r"(?:we assume|it is assumed|assuming that|on the assumption)\s+(.{15,200})",
        re.IGNORECASE,
    ),
    # Implicit assumptions: "X has been approved", "X is available"
    re.compile(
        r"((?:budget|funding|team|resource|infrastructure|access|environment)\s+"
        r"(?:has been|is|will be|was)\s+(?:approved|available|confirmed|provided|allocated|set up).{0,80})",
        re.IGNORECASE,
    ),
    # Conditional statements as implicit assumptions
    re.compile(
        r"((?:provided that|on condition that|subject to)\s+.{15,150})",
        re.IGNORECASE,
    ),
    # "Board/leadership has approved" patterns
    re.compile(
        r"((?:board|leadership|management|client|stakeholder)s?\s+"
        r"(?:has|have|had)\s+(?:approved|confirmed|agreed|signed off).{0,100})",
        re.IGNORECASE,
    ),
    # Budget as assumption
    re.compile(
        r"((?:budget|funding)\s+(?:of|is|:)\s*\$?[\d,.]+[KMB]?.{0,60})",
        re.IGNORECASE,
    ),
]

# ──────────────────────────────────────────────────────────────
# Dependency patterns
# ──────────────────────────────────────────────────────────────

DEPENDENCY_HEADING_KEYWORDS = [
    "dependency", "dependencies", "dependent on", "requires",
    "prerequisites", "blockers", "upstream", "downstream",
]

DEPENDENCY_INLINE_PATTERNS = [
    # Explicit dependency declarations
    re.compile(
        r"(?:depends? on|dependent on|blocked by|waiting for)\s+(.{15,200})",
        re.IGNORECASE,
    ),
    # Bullet items with dependency keywords
    re.compile(
        r"[-*•]\s*(?:dependency|blocked by|waiting on)\s*[:–-]?\s*(.{15,200})",
        re.IGNORECASE,
    ),
    # Sequencing language
    re.compile(
        r"(.{10,60})\s+must be completed before\s+(.{10,100})",
        re.IGNORECASE,
    ),
    # "X before Y" patterns
    re.compile(
        r"(.{10,60})\s+(?:before|prior to|ahead of)\s+(?:the\s+)?(.{10,100}cutover|migration|deployment|go-live)",
        re.IGNORECASE,
    ),
]

# ──────────────────────────────────────────────────────────────
# Constraint patterns
# ──────────────────────────────────────────────────────────────

CONSTRAINT_HEADING_KEYWORDS = [
    "constraint", "constraints", "limitations", "restrictions",
    "non-negotiable", "additional constraints",
    "security constraints", "operational constraints",
]

# Headings that look like constraints but are actually informational context
# (list standards/systems rather than imposing constraints)
CONSTRAINT_HEADING_EXCLUSIONS = [
    "compliance/regulatory",  # Lists standards, not constraints
    "third-party", "third party",  # Lists vendor systems
    "technology", "technology domains", "key technology",
    "application portfolio", "current state",
    "integrations",
]

CONSTRAINT_INLINE_PATTERNS = [
    # Explicit constraint declarations
    re.compile(
        r"(?:constraint|limitation|restriction)\s*[:–-]\s*(.{15,200})",
        re.IGNORECASE,
    ),
    # "Must" / "Must not" / "Cannot" hard requirements
    re.compile(
        r"((?:must|must not|cannot|shall not|no\s+\w+\s+can)\s+.{15,150})",
        re.IGNORECASE,
    ),
    # SLA / uptime / availability with numbers
    re.compile(
        r"((?:SLA|uptime|availability).{0,10}(?:requires?|of|:)\s*\d+.{0,80})",
        re.IGNORECASE,
    ),
    # Specific compliance standards with context
    re.compile(
        r"((?:HIPAA|PCI-DSS|PCI DSS|SOC\s*2|GDPR|SOX|ISO\s*27001).{0,80}(?:compliance|required|requirement|certification|standard).{0,40})",
        re.IGNORECASE,
    ),
    # "No X during Y" operational constraints
    re.compile(
        r"(no\s+(?:downtime|disruption|outage|changes?).{0,60}(?:during|between|within).{0,80})",
        re.IGNORECASE,
    ),
    # Data residency / sovereignty
    re.compile(
        r"((?:data|records?)\s+(?:cannot|must not|shall not)\s+(?:leave|exit|traverse).{0,100})",
        re.IGNORECASE,
    ),
    # Encryption requirements
    re.compile(
        r"((?:encrypt(?:ed|ion)?)\s+(?:at rest|in transit|end.to.end).{0,80})",
        re.IGNORECASE,
    ),
]

# ──────────────────────────────────────────────────────────────
# Resource patterns
# ──────────────────────────────────────────────────────────────

RESOURCE_HEADING_KEYWORDS = [
    "resource", "resources", "team", "staffing", "capacity",
    "resource requirements", "resource plan", "allocation",
]

RESOURCE_INLINE_PATTERNS = [
    # "Nx Role (duration)" pattern
    re.compile(
        r"(\d+)\s*x?\s*(senior|junior|mid[- ]?level|lead|principal)?\s*"
        r"(cloud\s+)?(?:engineer|developer|architect|manager|specialist|consultant|analyst|dba)"
        r"(?:\s*\(.{5,50}\))?",
        re.IGNORECASE,
    ),
    # "Team of N" or "Need N engineers"
    re.compile(
        r"(?:team of|need|require|hire)\s+(\d+)\s+"
        r"(?:additional\s+)?(?:senior\s+|junior\s+|lead\s+)?"
        r"(\w+(?:\s+\w+)?(?:engineers?|developers?|architects?|specialists?))",
        re.IGNORECASE,
    ),
    # Duration-based resource mentions
    re.compile(
        r"((?:full[- ]time|part[- ]time|contractor|FTE).{0,60}(?:\d+\s*(?:weeks?|months?|days?)))",
        re.IGNORECASE,
    ),
]

# ──────────────────────────────────────────────────────────────
# Action item patterns
# ──────────────────────────────────────────────────────────────

ACTION_HEADING_KEYWORDS = [
    "action item", "action items", "actions", "next steps",
    "follow-up", "follow up", "todo", "to-do",
]

ACTION_INLINE_PATTERNS = [
    # "Person: task" pattern (assignee with task)
    re.compile(
        r"[-*•]\s*([A-Z][A-Za-z\s.]{2,25}?)\s*[:–-]\s*(.{15,200})",
    ),
    # Explicit action/todo markers
    re.compile(
        r"(?:action|todo|follow[- ]?up)\s*[:–-]\s*(.{15,200})",
        re.IGNORECASE,
    ),
    # "X to do Y by Z" pattern
    re.compile(
        r"([A-Z][A-Za-z\s.]+?)\s+to\s+(.{15,100}?)\s+by\s+(.{5,30})",
    ),
]

# ──────────────────────────────────────────────────────────────
# Scope patterns
# ──────────────────────────────────────────────────────────────

SCOPE_HEADING_KEYWORDS = [
    "scope", "scope of work", "objectives", "deliverables",
    "executive summary", "overview", "goals", "current state",
    "current architecture", "target state", "recommended",
]


def matches_heading(heading: str, keywords: List[str], exclusions: List[str] = None) -> bool:
    """Check if a section heading matches any keyword but not exclusions."""
    heading_lower = heading.lower().strip()
    if exclusions:
        if any(ex in heading_lower for ex in exclusions):
            return False
    return any(kw in heading_lower for kw in keywords)


def extract_by_patterns(text: str, patterns: List[re.Pattern]) -> List[str]:
    """Extract matches from text using a list of regex patterns.

    Returns deduplicated, cleaned match strings.
    Filters out noise (table syntax, too short, too long).
    """
    results: List[str] = []
    for pattern in patterns:
        for match in pattern.finditer(text):
            # Use the last non-None group
            groups = [g for g in match.groups() if g]
            if groups:
                value = clean_extraction(groups[-1])
            else:
                value = clean_extraction(match.group(0))

            # Quality filters
            if not value:
                continue
            if len(value) < MIN_EXTRACTION_LENGTH:
                continue
            if len(value) > MAX_EXTRACTION_LENGTH:
                value = value[:MAX_EXTRACTION_LENGTH].rsplit(" ", 1)[0] + "..."
            if is_noise_line(value):
                continue
            if value not in results:
                results.append(value)
    return results


def extract_bullet_items(text: str) -> List[str]:
    """Extract bullet-pointed items from text.

    Filters out table fragments and noise.
    """
    bullet_re = re.compile(r"^\s*[-*•]\s+(.+)$", re.MULTILINE)
    items = []
    for m in bullet_re.finditer(text):
        item = clean_extraction(m.group(1))
        if len(item) >= MIN_EXTRACTION_LENGTH and not is_noise_line(item):
            items.append(item)
    return items


def extract_numbered_items(text: str) -> List[str]:
    """Extract numbered list items from text."""
    numbered_re = re.compile(r"^\s*\d+[.)]\s+(.+)$", re.MULTILINE)
    items = []
    for m in numbered_re.finditer(text):
        item = clean_extraction(m.group(1))
        if len(item) >= MIN_EXTRACTION_LENGTH and not is_noise_line(item):
            items.append(item)
    return items


def extract_from_table(text: str, target_column: int = 0) -> List[str]:
    """Extract items from a specific column of a markdown table.

    Used for structured risk tables where Risk/Impact/Likelihood columns exist.

    Args:
        text: Section content containing a markdown table.
        target_column: 0-indexed column to extract from.

    Returns:
        List of cell values from the target column.
    """
    rows = extract_table_rows(text)
    items = []
    for row in rows:
        if target_column < len(row):
            value = clean_extraction(row[target_column])
            if len(value) >= MIN_EXTRACTION_LENGTH:
                items.append(value)
    return items
