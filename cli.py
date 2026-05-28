"""Project Delivery Accelerator Engine – CLI Interface.

Run the full workflow from the command line without the server:
- Create and manage projects
- Ingest documents
- Build intelligence
- Run persona reviews
- View history and comparisons
- Export results

Usage:
    python cli.py <command> [options]

Commands:
    projects          List all projects
    create            Create a new project
    ingest            Ingest files into a project
    build             Build intelligence from ingested documents
    review            Run a persona review
    summary           Show project context summary
    personas          List available personas
    versions          List context build versions
    compare           Compare two versions
    evolution         Show category evolution timeline
    reviews           Show review history
    export            Export intelligence or reviews to file
    status            Full project status overview
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

import project_manager


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="accelerator",
        description="Project Delivery Accelerator Engine – CLI",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # ── projects ──
    subparsers.add_parser("projects", help="List all projects")

    # ── create ──
    create_parser = subparsers.add_parser("create", help="Create a new project")
    create_parser.add_argument("name", help="Project name")
    create_parser.add_argument("-d", "--description", default="", help="Project description")

    # ── ingest ──
    ingest_parser = subparsers.add_parser("ingest", help="Ingest files into a project")
    ingest_parser.add_argument("project_id", help="Project ID (e.g. proj-001)")
    ingest_parser.add_argument("files", nargs="+", help="File paths to ingest")

    # ── build ──
    build_parser = subparsers.add_parser("build", help="Build intelligence from documents")
    build_parser.add_argument("project_id", help="Project ID")
    build_parser.add_argument("-l", "--label", default=None, help="Version label")

    # ── review ──
    review_parser = subparsers.add_parser("review", help="Run a persona review")
    review_parser.add_argument("project_id", help="Project ID")
    review_parser.add_argument("persona", help="Persona ID (e.g. solution_architect)")
    review_parser.add_argument(
        "-b", "--backend", default="files_only",
        choices=["files_only", "ollama", "bedrock"],
        help="AI backend (default: files_only)",
    )

    # ── summary ──
    summary_parser = subparsers.add_parser("summary", help="Show context summary")
    summary_parser.add_argument("project_id", help="Project ID")

    # ── personas ──
    subparsers.add_parser("personas", help="List available personas")

    # ── versions ──
    versions_parser = subparsers.add_parser("versions", help="List context versions")
    versions_parser.add_argument("project_id", help="Project ID")

    # ── compare ──
    compare_parser = subparsers.add_parser("compare", help="Compare two versions")
    compare_parser.add_argument("project_id", help="Project ID")
    compare_parser.add_argument("version_a", help="First version (e.g. v1)")
    compare_parser.add_argument("version_b", help="Second version (e.g. v2)")

    # ── evolution ──
    evolution_parser = subparsers.add_parser("evolution", help="Show category evolution")
    evolution_parser.add_argument("project_id", help="Project ID")
    evolution_parser.add_argument(
        "category", nargs="?", default="risks",
        choices=["risks", "assumptions", "dependencies", "constraints", "action_items"],
        help="Category to track (default: risks)",
    )

    # ── reviews ──
    reviews_parser = subparsers.add_parser("reviews", help="Show review history")
    reviews_parser.add_argument("project_id", help="Project ID")
    reviews_parser.add_argument("-p", "--persona", default=None, help="Filter by persona ID")

    # ── export ──
    export_parser = subparsers.add_parser("export", help="Export to file")
    export_parser.add_argument("project_id", help="Project ID")
    export_parser.add_argument(
        "what", choices=["intelligence", "reviews", "summary", "all"],
        help="What to export",
    )
    export_parser.add_argument("-o", "--output", default=None, help="Output file path")
    export_parser.add_argument(
        "-f", "--format", default="markdown", choices=["markdown", "json"],
        help="Output format (default: markdown)",
    )

    # ── proposal ──
    proposal_parser = subparsers.add_parser("proposal", help="Manage proposals")
    proposal_sub = proposal_parser.add_subparsers(dest="proposal_cmd")

    prop_create = proposal_sub.add_parser("create", help="Create proposal")
    prop_create.add_argument("project_id", help="Project ID")
    prop_create.add_argument("name", help="Proposal name")
    prop_create.add_argument("-c", "--client", default="", help="Client name")
    prop_create.add_argument("--files", nargs="*", default=[], help="Associated files")
    prop_create.add_argument("-n", "--notes", default="", help="Notes")

    prop_version = proposal_sub.add_parser("add-version", help="Add proposal version")
    prop_version.add_argument("project_id", help="Project ID")
    prop_version.add_argument("-l", "--label", default="", help="Version label")
    prop_version.add_argument("--files", nargs="*", default=[], help="Files")
    prop_version.add_argument("--changes", default="", help="What changed")
    prop_version.add_argument("-n", "--notes", default="", help="Notes")

    prop_list = proposal_sub.add_parser("list", help="List proposal versions")
    prop_list.add_argument("project_id", help="Project ID")

    prop_compare = proposal_sub.add_parser("compare", help="Compare proposal versions")
    prop_compare.add_argument("project_id", help="Project ID")
    prop_compare.add_argument("version_a", help="First version (e.g. prop-v1)")
    prop_compare.add_argument("version_b", help="Second version (e.g. prop-v2)")

    prop_status = proposal_sub.add_parser("set-status", help="Set proposal version status")
    prop_status.add_argument("project_id", help="Project ID")
    prop_status.add_argument("version_id", help="Version ID (e.g. prop-v1)")
    prop_status.add_argument("status", help="New status")

    prop_info = proposal_sub.add_parser("info", help="Show proposal details")
    prop_info.add_argument("project_id", help="Project ID")

    # ── phase ──
    phase_parser = subparsers.add_parser("phase", help="Manage project phases")
    phase_sub = phase_parser.add_subparsers(dest="phase_cmd")

    phase_transition = phase_sub.add_parser("transition", help="Transition to new phase")
    phase_transition.add_argument("project_id", help="Project ID")
    phase_transition.add_argument("new_phase", help="Target phase")
    phase_transition.add_argument("-r", "--reason", default="", help="Reason for transition")

    phase_history = phase_sub.add_parser("history", help="View phase history")
    phase_history.add_argument("project_id", help="Project ID")

    phase_info = phase_sub.add_parser("info", help="Show available phases and transitions")

    # ── status ──
    status_parser = subparsers.add_parser("status", help="Full project status")
    status_parser.add_argument("project_id", help="Project ID")

    # Parse args
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    # Route to command handler
    try:
        handlers = {
            "projects": cmd_projects,
            "create": cmd_create,
            "ingest": cmd_ingest,
            "build": cmd_build,
            "review": cmd_review,
            "summary": cmd_summary,
            "personas": cmd_personas,
            "versions": cmd_versions,
            "compare": cmd_compare,
            "evolution": cmd_evolution,
            "reviews": cmd_reviews,
            "export": cmd_export,
            "status": cmd_status,
            "proposal": cmd_proposal,
            "phase": cmd_phase,
        }
        handler = handlers.get(args.command)
        if handler:
            handler(args)
        else:
            parser.print_help()
    except ValueError as e:
        _error(str(e))
    except Exception as e:
        _error(f"Unexpected error: {e}")


# ──────────────────────────────────────────────────────────────
# Command handlers
# ──────────────────────────────────────────────────────────────


def cmd_projects(args) -> None:
    """List all projects."""
    projects = project_manager.list_projects()
    if not projects:
        _info("No projects yet. Create one with: python cli.py create <name>")
        return

    _header("Projects")
    for p in projects:
        phase = p.get("phase", "discovery")
        files = p.get("file_count", 0)
        print(f"  {p['id']}  {p['name']:<30}  phase: {phase:<12}  files: {files}")


def cmd_create(args) -> None:
    """Create a new project."""
    project = project_manager.create_project(args.name, args.description)
    _success(f"Created project: {project['id']} – {project['name']}")
    _info(f"Next: python cli.py ingest {project['id']} <files...>")


def cmd_ingest(args) -> None:
    """Ingest files into a project."""
    paths = [Path(f) for f in args.files]

    # Validate files exist
    for p in paths:
        if not p.exists():
            _error(f"File not found: {p}")
            return

    result = project_manager.ingest_files_to_project(args.project_id, paths)

    _header(f"Ingestion Results – {args.project_id}")
    print(f"  Ingested: {result['ingested']} file(s)")
    if result["documents"]:
        for doc in result["documents"]:
            print(f"    ✓ {doc['filename']} ({doc['source_type']}, {doc['sections']} sections, {doc['word_count']} words)")
    if result["errors"]:
        print(f"  Errors: {len(result['errors'])}")
        for err in result["errors"]:
            print(f"    ✗ {err['file']}: {err['error']}")

    _info(f"Next: python cli.py build {args.project_id}")


def cmd_build(args) -> None:
    """Build intelligence from ingested documents."""
    result = project_manager.build_project_intelligence(args.project_id, args.label)
    meta = result.get("_build_metadata", {})
    version = result.get("_version", {})

    _header(f"Intelligence Built – {args.project_id}")
    print(f"  Version:      {version.get('version_id', '?')} ({version.get('label', '')})")
    print(f"  Documents:    {meta.get('document_count', 0)}")
    print(f"  Risks:        {meta.get('total_risks', 0)}")
    print(f"  Assumptions:  {meta.get('total_assumptions', 0)}")
    print(f"  Dependencies: {meta.get('total_dependencies', 0)}")
    print(f"  Constraints:  {meta.get('total_constraints', 0)}")
    print(f"  Action Items: {meta.get('total_action_items', 0)}")

    _info(f"Next: python cli.py review {args.project_id} solution_architect")


def cmd_review(args) -> None:
    """Run a persona review."""
    result = project_manager.run_persona_review(
        args.project_id, args.persona, args.backend
    )

    _header(f"{result['persona']} Review – {args.project_id}")
    print(f"  Backend: {result['ai_backend']}")
    print(f"  Time:    {result['timestamp']}")
    print()

    findings = result.get("findings", {})
    for section, items in findings.items():
        if items:
            print(f"  {_format_section_name(section)} ({len(items)}):")
            for item in items:
                print(f"    • {item[:120]}")
            print()

    if result.get("questions"):
        print(f"  Open Questions:")
        for q in result["questions"]:
            print(f"    ? {q}")
        print()

    print(f"  Summary: {result.get('summary', '')}")


def cmd_summary(args) -> None:
    """Show context summary."""
    summary = project_manager.get_project_summary(args.project_id)
    print(summary)


def cmd_personas(args) -> None:
    """List available personas."""
    from personas.engine import list_personas

    _header("Available Personas")
    for p in list_personas():
        print(f"  {p['id']:<22} {p['name']:<22} {p['role'][:60]}")


def cmd_versions(args) -> None:
    """List context build versions."""
    versions = project_manager.get_project_versions(args.project_id)
    if not versions:
        _info("No versions yet. Build intelligence first: python cli.py build <project_id>")
        return

    _header(f"Context Versions – {args.project_id}")
    for v in versions:
        stats = v.get("stats", {})
        print(
            f"  {v['version_id']}  {v.get('label', ''):<20}  "
            f"risks:{stats.get('risks', 0):>2}  deps:{stats.get('dependencies', 0):>2}  "
            f"constraints:{stats.get('constraints', 0):>2}  "
            f"docs:{stats.get('document_count', 0):>2}  "
            f"{v['timestamp'][:16]}"
        )


def cmd_compare(args) -> None:
    """Compare two context versions."""
    comparison = project_manager.compare_project_versions(
        args.project_id, args.version_a, args.version_b
    )

    _header(f"Version Comparison: {args.version_a} → {args.version_b}")
    print()

    for category, data in comparison.get("categories", {}).items():
        net = data["net_change"]
        direction = "↑" if net > 0 else ("↓" if net < 0 else "→")
        print(f"  {category:<15} {data['count_before']:>3} → {data['count_after']:>3}  {direction} ({net:+d})")

        if data.get("added"):
            for item in data["added"][:3]:
                print(f"      + {item[:80]}")
        if data.get("removed"):
            for item in data["removed"][:3]:
                print(f"      - {item[:80]}")
        print()

    summary = comparison.get("summary", {})
    print(f"  Trend: {summary.get('trend', 'unknown')}")
    print(f"  Net change: +{summary.get('total_added', 0)} added, -{summary.get('total_removed', 0)} removed")


def cmd_evolution(args) -> None:
    """Show category evolution across versions."""
    timeline = project_manager.get_project_evolution(args.project_id, args.category)
    if not timeline:
        _info("No versions yet. Build intelligence first.")
        return

    _header(f"Evolution: {args.category} – {args.project_id}")
    max_count = max(t["count"] for t in timeline) if timeline else 1

    for t in timeline:
        bar_len = int((t["count"] / max(max_count, 1)) * 30)
        bar = "█" * bar_len
        print(f"  {t['version_id']:<4} {t.get('label', ''):<20} {bar} {t['count']}")


def cmd_reviews(args) -> None:
    """Show review history."""
    history = project_manager.get_project_review_history(args.project_id, args.persona)
    if not history:
        _info("No reviews yet. Run one with: python cli.py review <project_id> <persona>")
        return

    _header(f"Review History – {args.project_id}")
    for r in history:
        print(
            f"  {r['timestamp'][:16]}  {r['persona']:<22}  "
            f"{r['ai_backend']:<12}  findings: {r['total_findings']}"
        )


def cmd_export(args) -> None:
    """Export intelligence or reviews."""
    output_path = args.output
    fmt = args.format

    if args.what == "intelligence":
        data = project_manager.get_project_intelligence(args.project_id)
        if not data:
            _error("No intelligence built yet.")
            return
        content = _format_export(data, fmt, "intelligence")
    elif args.what == "reviews":
        data = project_manager.get_project_review_history(args.project_id)
        if not data:
            _error("No reviews yet.")
            return
        content = _format_export(data, fmt, "reviews")
    elif args.what == "summary":
        content = project_manager.get_project_summary(args.project_id)
        fmt = "markdown"  # Summary is always markdown
    elif args.what == "all":
        content = _export_all(args.project_id, fmt)
    else:
        _error(f"Unknown export target: {args.what}")
        return

    if output_path:
        Path(output_path).write_text(content)
        _success(f"Exported to: {output_path}")
    else:
        # Default output path
        ext = "md" if fmt == "markdown" else "json"
        default_path = f"outputs/{args.project_id}_{args.what}.{ext}"
        Path(default_path).parent.mkdir(parents=True, exist_ok=True)
        Path(default_path).write_text(content)
        _success(f"Exported to: {default_path}")


def cmd_status(args) -> None:
    """Full project status overview."""
    project = project_manager.get_project(args.project_id)
    if not project:
        _error(f"Project not found: {args.project_id}")
        return

    _header(f"Project Status: {project['name']}")
    print(f"  ID:          {project['id']}")
    print(f"  Phase:       {project.get('phase', 'discovery')}")
    print(f"  AI Backend:  {project.get('ai_backend', 'ollama')}")
    print(f"  Files:       {len(project.get('files', []))}")
    print(f"  Created:     {project.get('created_at', '')[:16]}")
    print(f"  Updated:     {project.get('updated_at', '')[:16]}")

    iteration = project.get("iteration") or {}
    if iteration:
        print()
        print(f"  Iteration:")
        print(f"    Current version: {iteration.get('current_version', '-')}")
        print(f"    Total builds:    {iteration.get('total_builds', 0)}")
        print(f"    Total reviews:   {iteration.get('total_reviews', 0)}")
        print(f"    Last build:      {(iteration.get('last_build_at', '') or '-')[:16]}")
        print(f"    Last review:     {(iteration.get('last_review_at', '') or '-')[:16]}")

    # Quick intelligence summary
    intelligence = project_manager.get_project_intelligence(args.project_id)
    if intelligence:
        meta = intelligence.get("_build_metadata", {})
        print()
        print(f"  Intelligence:")
        print(f"    Risks:        {meta.get('total_risks', 0)}")
        print(f"    Constraints:  {meta.get('total_constraints', 0)}")
        print(f"    Dependencies: {meta.get('total_dependencies', 0)}")
        print(f"    Assumptions:  {meta.get('total_assumptions', 0)}")
        print(f"    Action Items: {meta.get('total_action_items', 0)}")


def cmd_proposal(args) -> None:
    """Handle proposal subcommands."""
    if not args.proposal_cmd:
        _info("Usage: python cli.py proposal {create|add-version|list|compare|set-status|info} ...")
        return

    if args.proposal_cmd == "create":
        result = project_manager.create_proposal(
            args.project_id, args.name, args.client,
            [Path(f) for f in args.files] if args.files else None,
            args.notes,
        )
        _success(f"Proposal created: {result['proposal_name']}")
        _info(f"Version: {result['current_version']}")

    elif args.proposal_cmd == "add-version":
        result = project_manager.add_proposal_version(
            args.project_id, args.label,
            [Path(f) for f in args.files] if args.files else None,
            args.notes, args.changes,
        )
        _success(f"Proposal version added: {result['version_id']} – {result['label']}")

    elif args.proposal_cmd == "list":
        versions = project_manager.list_proposal_versions_for_project(args.project_id)
        if not versions:
            _info("No proposal yet. Create one: python cli.py proposal create <project_id> <name>")
            return
        _header(f"Proposal Versions – {args.project_id}")
        for v in versions:
            status_icon = {"draft": "○", "submitted": "→", "under_review": "◎",
                          "accepted": "✓", "rejected": "✗", "superseded": "↓",
                          "revised": "↻"}.get(v["status"], "?")
            print(f"  {status_icon} {v['version_id']}  {v['label']:<25}  "
                  f"status: {v['status']:<13}  files: {v['files_count']}  "
                  f"{v['created_at'][:16]}")

    elif args.proposal_cmd == "compare":
        result = project_manager.compare_proposals(
            args.project_id, args.version_a, args.version_b
        )
        _header(f"Proposal Comparison: {result['version_a']} → {result['version_b']}")
        print(f"  {result['label_a']} ({result['status_a']}) → {result['label_b']} ({result['status_b']})")
        print(f"  Time between: {result['time_between']}")
        print()
        files = result.get("files", {})
        if files.get("added"):
            print(f"  Files added:")
            for f in files["added"]:
                print(f"    + {f}")
        if files.get("removed"):
            print(f"  Files removed:")
            for f in files["removed"]:
                print(f"    - {f}")
        if result.get("changes_noted"):
            print(f"\n  Changes noted: {result['changes_noted']}")

    elif args.proposal_cmd == "set-status":
        result = project_manager.update_proposal_status(
            args.project_id, args.version_id, args.status
        )
        _success(f"Status updated: {result['version_id']} → {result['status']}")

    elif args.proposal_cmd == "info":
        proposal = project_manager.get_proposal_info(args.project_id)
        if not proposal:
            _info("No proposal exists for this project.")
            return
        _header(f"Proposal: {proposal['proposal_name']}")
        print(f"  Client:          {proposal.get('client', '-')}")
        print(f"  Current version: {proposal['current_version']}")
        print(f"  Total versions:  {proposal['total_versions']}")
        print(f"  Created:         {proposal['created_at'][:16]}")
        print(f"  Updated:         {proposal['updated_at'][:16]}")


def cmd_phase(args) -> None:
    """Handle phase subcommands."""
    if not args.phase_cmd:
        _info("Usage: python cli.py phase {transition|history|info} ...")
        return

    if args.phase_cmd == "transition":
        result = project_manager.transition_project_phase(
            args.project_id, args.new_phase, args.reason
        )
        _success(f"Phase transition: {result['from_phase']} → {result['to_phase']}")
        if result.get("reason"):
            _info(f"Reason: {result['reason']}")

    elif args.phase_cmd == "history":
        history = project_manager.get_phase_history_for_project(args.project_id)
        if not history:
            _info("No phase history yet.")
            return
        _header(f"Phase History – {args.project_id}")
        for entry in history:
            current_marker = " ← current" if entry.get("is_current") else ""
            print(
                f"  {entry['phase']:<12}  entered: {entry['entered_at'][:16]}  "
                f"duration: {entry.get('duration', '-')}{current_marker}"
            )
            if entry.get("reason"):
                print(f"                reason: {entry['reason']}")

    elif args.phase_cmd == "info":
        phases = project_manager.get_phase_info()
        _header("SDLC Phases")
        for p in phases:
            transitions = ", ".join(p["can_transition_to"]) or "none"
            print(f"  {p['order']}. {p['phase']:<12}  → can move to: {transitions}")


# ──────────────────────────────────────────────────────────────
# Export formatters
# ──────────────────────────────────────────────────────────────


def _format_export(data, fmt: str, data_type: str) -> str:
    """Format data for export."""
    if fmt == "json":
        return json.dumps(data, indent=2)

    # Markdown format
    if data_type == "intelligence":
        return _intelligence_to_markdown(data)
    elif data_type == "reviews":
        return _reviews_to_markdown(data)
    return json.dumps(data, indent=2)


def _intelligence_to_markdown(data: dict) -> str:
    """Convert intelligence to markdown report."""
    lines = ["# Project Intelligence Report", ""]
    meta = data.get("_build_metadata", {})
    lines.append(f"*Generated from {meta.get('document_count', '?')} documents*")
    lines.append("")

    if data.get("scope"):
        lines.append("## Scope")
        lines.append(data["scope"])
        lines.append("")

    for category in ["risks", "assumptions", "dependencies", "constraints", "action_items"]:
        items = data.get(category, [])
        if items:
            title = category.replace("_", " ").title()
            lines.append(f"## {title}")
            lines.append("")
            for item in items:
                if isinstance(item, dict):
                    lines.append(f"- {item.get('description', str(item))}")
                else:
                    lines.append(f"- {item}")
            lines.append("")

    return "\n".join(lines)


def _reviews_to_markdown(data: list) -> str:
    """Convert review history to markdown."""
    lines = ["# Review History", ""]
    for review in data:
        lines.append(f"## {review.get('persona', 'Unknown')} – {review.get('timestamp', '')[:16]}")
        lines.append(f"Backend: {review.get('ai_backend', '')}")
        lines.append(f"Findings: {review.get('total_findings', 0)}")
        lines.append("")
    return "\n".join(lines)


def _export_all(project_id: str, fmt: str) -> str:
    """Export everything for a project."""
    intelligence = project_manager.get_project_intelligence(project_id)
    reviews = project_manager.get_project_review_history(project_id)
    summary = project_manager.get_project_summary(project_id)

    if fmt == "json":
        return json.dumps({
            "intelligence": intelligence,
            "reviews": reviews,
            "summary": summary,
        }, indent=2)

    # Markdown
    lines = ["# Full Project Export", ""]
    lines.append(summary)
    lines.append("")
    lines.append("---")
    lines.append("")
    if intelligence:
        lines.append(_intelligence_to_markdown(intelligence))
    if reviews:
        lines.append(_reviews_to_markdown(reviews))
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────
# Output helpers
# ──────────────────────────────────────────────────────────────


def _header(text: str) -> None:
    """Print a section header."""
    print(f"\n{'─' * 60}")
    print(f"  {text}")
    print(f"{'─' * 60}")


def _info(text: str) -> None:
    """Print info message."""
    print(f"\n  ℹ {text}")


def _success(text: str) -> None:
    """Print success message."""
    print(f"\n  ✓ {text}")


def _error(text: str) -> None:
    """Print error and exit."""
    print(f"\n  ✗ Error: {text}", file=sys.stderr)
    sys.exit(1)


def _format_section_name(name: str) -> str:
    """Format a section key into a readable name."""
    return name.replace("_", " ").title()


if __name__ == "__main__":
    main()
