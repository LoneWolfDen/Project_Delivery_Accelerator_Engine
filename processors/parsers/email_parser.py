"""Email parser.

Handles .eml files and text-based email formats.
Extracts headers (From, To, Subject, Date) and body content.
"""

import email
import re
from email import policy
from pathlib import Path
from typing import List, Optional

from models.document import (
    ContentType,
    DocumentMetadata,
    DocumentSection,
    IngestedDocument,
    SourceType,
)

# Pattern for detecting email-like headers in plain text
EMAIL_HEADER_PATTERN = re.compile(
    r"^(From|To|Cc|Bcc|Subject|Date|Sent|Received):\s*(.+)$", re.IGNORECASE
)


def parse(file_path: Path) -> IngestedDocument:
    """Parse an email file into an IngestedDocument.

    Supports:
    - .eml files (RFC 2822 format)
    - .txt files with email headers

    Args:
        file_path: Path to the email file.

    Returns:
        IngestedDocument with email metadata and body sections.
    """
    raw_text = file_path.read_text(encoding="utf-8", errors="replace")

    if file_path.suffix.lower() == ".eml":
        return _parse_eml(file_path, raw_text)
    else:
        return _parse_text_email(file_path, raw_text)


def _parse_eml(file_path: Path, raw_text: str) -> IngestedDocument:
    """Parse a proper .eml file using the email module."""
    msg = email.message_from_string(raw_text, policy=policy.default)

    subject = msg.get("Subject", "")
    from_addr = msg.get("From", "")
    to_addr = msg.get("To", "")
    cc_addr = msg.get("Cc", "")
    date_str = msg.get("Date", "")

    # Extract body
    body = _get_email_body(msg)

    # Build participants list
    participants = _extract_participants(from_addr, to_addr, cc_addr)

    # Build sections
    sections = _build_email_sections(subject, from_addr, to_addr, date_str, body)

    metadata = DocumentMetadata(
        title=subject or file_path.stem,
        subject=subject,
        source_type=SourceType.EMAIL,
        date=date_str,
        author=from_addr,
        participants=participants,
        word_count=len(body.split()),
        line_count=len(body.splitlines()),
    )

    return IngestedDocument(
        filename=file_path.name,
        file_path=str(file_path),
        content_type=ContentType.EMAIL,
        metadata=metadata,
        sections=sections,
        raw_text=raw_text,
    )


def _parse_text_email(file_path: Path, raw_text: str) -> IngestedDocument:
    """Parse a text file that looks like an email (has From/To/Subject headers)."""
    lines = raw_text.splitlines()
    headers: dict = {}
    body_start = 0

    # Extract headers from top of file
    for i, line in enumerate(lines):
        match = EMAIL_HEADER_PATTERN.match(line)
        if match:
            headers[match.group(1).lower()] = match.group(2).strip()
            body_start = i + 1
        elif line.strip() == "" and headers:
            body_start = i + 1
            break
        elif not headers:
            # No headers at all, treat as plain text
            break

    if not headers:
        # Not actually an email, fall back
        from processors.parsers.plain_text import parse as plain_parse
        return plain_parse(file_path)

    body = "\n".join(lines[body_start:]).strip()
    subject = headers.get("subject", "")
    from_addr = headers.get("from", "")
    to_addr = headers.get("to", "")
    date_str = headers.get("date", headers.get("sent", ""))

    participants = _extract_participants(from_addr, to_addr, headers.get("cc", ""))
    sections = _build_email_sections(subject, from_addr, to_addr, date_str, body)

    metadata = DocumentMetadata(
        title=subject or file_path.stem,
        subject=subject,
        source_type=SourceType.EMAIL,
        date=date_str,
        author=from_addr,
        participants=participants,
        word_count=len(body.split()),
        line_count=len(body.splitlines()),
    )

    return IngestedDocument(
        filename=file_path.name,
        file_path=str(file_path),
        content_type=ContentType.EMAIL,
        metadata=metadata,
        sections=sections,
        raw_text=raw_text,
    )


def _get_email_body(msg: email.message.Message) -> str:
    """Extract plain text body from email message."""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode("utf-8", errors="replace")
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            return payload.decode("utf-8", errors="replace")
    return ""


def _extract_participants(from_addr: str, to_addr: str, cc_addr: str) -> List[str]:
    """Build a deduplicated list of all email participants."""
    participants = []
    for field_val in [from_addr, to_addr, cc_addr]:
        if field_val:
            # Split on comma for multiple recipients
            for addr in field_val.split(","):
                addr = addr.strip()
                if addr and addr not in participants:
                    participants.append(addr)
    return participants


def _build_email_sections(
    subject: str, from_addr: str, to_addr: str, date_str: str, body: str
) -> List[DocumentSection]:
    """Build structured sections for an email."""
    sections: List[DocumentSection] = []

    # Header section
    header_content = f"From: {from_addr}\nTo: {to_addr}\nDate: {date_str}\nSubject: {subject}"
    sections.append(DocumentSection(
        heading="Email Headers",
        content=header_content,
        section_type="metadata",
        line_start=0,
        line_end=3,
    ))

    # Body section(s)
    if body:
        body_lines = body.splitlines()
        sections.append(DocumentSection(
            heading="Email Body",
            content=body,
            section_type="body",
            line_start=4,
            line_end=4 + len(body_lines),
        ))

    return sections
