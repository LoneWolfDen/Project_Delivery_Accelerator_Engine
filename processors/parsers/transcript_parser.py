"""Meeting transcript parser.

Handles meeting transcripts with speaker turns, timestamps, and action items.
Supports common formats:
- "Speaker Name: content"
- "[HH:MM:SS] Speaker: content"
- "HH:MM - Speaker - content"
"""

import re
from pathlib import Path
from typing import List, Optional, Tuple

from models.document import (
    ContentType,
    DocumentMetadata,
    DocumentSection,
    IngestedDocument,
    SourceType,
)

# Speaker patterns (most specific first)
TIMESTAMPED_SPEAKER = re.compile(
    r"^\[?(\d{1,2}:\d{2}(?::\d{2})?)\]?\s*[-–]?\s*([A-Za-z][A-Za-z\s.]+?)\s*[-–:]\s*(.+)$"
)
SIMPLE_SPEAKER = re.compile(r"^([A-Z][A-Za-z\s.]+?)\s*:\s*(.+)$")

# Action item patterns
ACTION_ITEM_PATTERN = re.compile(
    r"(?:action item|action|todo|follow[- ]up|next step)s?\s*[:–-]\s*(.*)",
    re.IGNORECASE,
)
BULLET_ACTION = re.compile(r"^\s*[-*•]\s*\[?\s*\]?\s*(.+)$")


def parse(file_path: Path) -> IngestedDocument:
    """Parse a meeting transcript into an IngestedDocument.

    Args:
        file_path: Path to the transcript file.

    Returns:
        IngestedDocument with speaker turns and action items extracted.
    """
    raw_text = file_path.read_text(encoding="utf-8", errors="replace")
    lines = raw_text.splitlines()

    sections = _extract_speaker_turns(lines)
    action_items = _extract_action_items(lines)
    if action_items:
        sections.extend(action_items)

    participants = _extract_participants(sections)
    metadata = _build_metadata(raw_text, lines, file_path, participants)

    return IngestedDocument(
        filename=file_path.name,
        file_path=str(file_path),
        content_type=ContentType.TEXT,
        metadata=metadata,
        sections=sections,
        raw_text=raw_text,
    )


def _extract_speaker_turns(lines: List[str]) -> List[DocumentSection]:
    """Extract speaker turns from transcript lines."""
    sections: List[DocumentSection] = []
    current_speaker: Optional[str] = None
    current_timestamp: Optional[str] = None
    current_lines: List[str] = []
    section_start = 0

    for i, line in enumerate(lines):
        speaker, timestamp, content = _parse_line(line)

        if speaker:
            # Save previous turn
            if current_speaker and current_lines:
                sections.append(DocumentSection(
                    heading=current_speaker,
                    content="\n".join(current_lines).strip(),
                    section_type="speaker_turn",
                    speaker=current_speaker,
                    timestamp=current_timestamp,
                    line_start=section_start,
                    line_end=i - 1,
                ))
            current_speaker = speaker
            current_timestamp = timestamp
            current_lines = [content] if content else []
            section_start = i
        else:
            current_lines.append(line)

    # Final turn
    if current_speaker and current_lines:
        sections.append(DocumentSection(
            heading=current_speaker,
            content="\n".join(current_lines).strip(),
            section_type="speaker_turn",
            speaker=current_speaker,
            timestamp=current_timestamp,
            line_start=section_start,
            line_end=len(lines) - 1,
        ))

    # If no speaker turns detected, treat as unstructured
    if not sections and lines:
        sections.append(DocumentSection(
            heading="Transcript Body",
            content="\n".join(lines).strip(),
            section_type="body",
            line_start=0,
            line_end=len(lines) - 1,
        ))

    return sections


def _parse_line(line: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Try to parse a line as a speaker turn.

    Returns:
        (speaker, timestamp, content) or (None, None, None) if not a speaker turn.
    """
    # Try timestamped format first
    match = TIMESTAMPED_SPEAKER.match(line)
    if match:
        return match.group(2).strip(), match.group(1), match.group(3).strip()

    # Try simple "Speaker: content" format
    match = SIMPLE_SPEAKER.match(line)
    if match:
        speaker = match.group(1).strip()
        # Avoid false positives: skip if "speaker" is a common word
        if len(speaker.split()) <= 4 and not _is_common_prefix(speaker):
            return speaker, None, match.group(2).strip()

    return None, None, None


def _is_common_prefix(text: str) -> bool:
    """Check if text is a common non-speaker prefix (avoid false positives)."""
    common = {
        "note", "notes", "example", "summary", "context", "background",
        "action", "decision", "question", "answer", "update", "status",
        "risk", "issue", "topic", "agenda", "conclusion",
    }
    return text.lower() in common


def _extract_action_items(lines: List[str]) -> List[DocumentSection]:
    """Extract action items from the transcript."""
    action_sections: List[DocumentSection] = []
    in_action_block = False
    action_lines: List[str] = []
    block_start = 0

    for i, line in enumerate(lines):
        if ACTION_ITEM_PATTERN.search(line):
            in_action_block = True
            block_start = i
            action_match = ACTION_ITEM_PATTERN.search(line)
            remainder = action_match.group(1).strip() if action_match else ""
            if remainder:
                action_lines.append(remainder)
        elif in_action_block:
            bullet_match = BULLET_ACTION.match(line)
            if bullet_match:
                action_lines.append(bullet_match.group(1).strip())
            elif line.strip() == "":
                # End of action block only if we already have items
                if action_lines:
                    action_sections.append(DocumentSection(
                        heading="Action Items",
                        content="\n".join(f"- {item}" for item in action_lines),
                        section_type="action_item",
                        line_start=block_start,
                        line_end=i,
                    ))
                    action_lines = []
                    in_action_block = False
            else:
                # Non-bullet line in action block, might be continuation
                if line.strip():
                    action_lines.append(line.strip())

    # Final action block if file ends without blank line
    if action_lines:
        action_sections.append(DocumentSection(
            heading="Action Items",
            content="\n".join(f"- {item}" for item in action_lines),
            section_type="action_item",
            line_start=block_start,
            line_end=len(lines) - 1,
        ))

    return action_sections


def _extract_participants(sections: List[DocumentSection]) -> List[str]:
    """Get unique speaker names from speaker_turn sections."""
    speakers = []
    for section in sections:
        if section.section_type == "speaker_turn" and section.speaker:
            if section.speaker not in speakers:
                speakers.append(section.speaker)
    return speakers


def _build_metadata(
    raw_text: str, lines: List[str], file_path: Path, participants: List[str]
) -> DocumentMetadata:
    """Build metadata for a transcript."""
    return DocumentMetadata(
        title=file_path.stem.replace("_", " ").replace("-", " ").title(),
        source_type=SourceType.TRANSCRIPT if participants else SourceType.CALL_NOTES,
        participants=participants,
        word_count=len(raw_text.split()),
        line_count=len(lines),
    )
