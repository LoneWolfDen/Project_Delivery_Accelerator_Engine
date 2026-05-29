#!/usr/bin/env python3
"""Seed fresh SQLite test data for the Project Delivery Accelerator Engine.

Usage (from repo root):
    python scripts/seed_sqlite.py

Creates:
  - 2 test projects (pre-sales + delivery phase)
  - Standard phases for each project
  - 2 versions + 2 reviews per project
  - 1 artifact per project
  - 1 proposal with 2 versions (pre-sales project only)
  - Sample pre-sales feedback entry

All data is written to projects_data/accelerator.db and mirrored to JSON
files if file_write_enabled is True (default).
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure repo root is on sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from db.database import get_db, Database

NOW = datetime.now(timezone.utc)


def iso(offset_days: int = 0) -> str:
    from datetime import timedelta
    return (NOW - timedelta(days=offset_days)).isoformat()


def run():
    db = get_db()
    print(f"Seeding SQLite DB at: {db.path}")

    # ── Projects ──────────────────────────────────────────────
    projects = [
        {
            "id": "proj-test-001",
            "name": "Cloud Platform Migration (Test)",
            "description": "Migration of legacy on-prem workloads to AWS. Seed data.",
            "phase": "pre-sales",
            "ai_backend": "files_only",
            "status": "active",
            "settings": "{}",
            "files": "[]",
            "file_toggles": "{}",
            "iteration": json.dumps({"current_version": "v2", "total_builds": 2, "total_reviews": 2}),
            "created_at": iso(14),
            "updated_at": iso(1),
            "archived_at": "",
            "restored_at": "",
        },
        {
            "id": "proj-test-002",
            "name": "Digital Transformation Programme (Test)",
            "description": "Enterprise-wide digital transformation initiative. Seed data.",
            "phase": "delivery",
            "ai_backend": "files_only",
            "status": "active",
            "settings": "{}",
            "files": "[]",
            "file_toggles": "{}",
            "iteration": json.dumps({"current_version": "v1", "total_builds": 1, "total_reviews": 1}),
            "created_at": iso(30),
            "updated_at": iso(3),
            "archived_at": "",
            "restored_at": "",
        },
    ]
    for p in projects:
        db.execute(
            """INSERT OR REPLACE INTO projects
               (id, name, description, phase, ai_backend, status, settings,
                files, file_toggles, iteration, created_at, updated_at,
                archived_at, restored_at)
               VALUES (:id,:name,:description,:phase,:ai_backend,:status,:settings,
                       :files,:file_toggles,:iteration,:created_at,:updated_at,
                       :archived_at,:restored_at)""",
            p,
        )
    db.commit()
    print(f"  ✓ {len(projects)} projects inserted")

    # ── Phases ────────────────────────────────────────────────
    STANDARD_PHASES = [
        ("pre-sales", "Pre-sales",  1, "Client engagement, proposals, scoping"),
        ("design",    "Design",     2, "Architecture, solution design, planning"),
        ("delivery",  "Delivery",   3, "Execution, development, implementation"),
        ("support",   "Support",    4, "Operations, maintenance, handover"),
    ]
    phase_rows = []
    for pid, (proj_id, current_phase) in [
        ("proj-test-001", ("proj-test-001", "pre-sales")),
        ("proj-test-002", ("proj-test-002", "delivery")),
    ]:
        for ph_id, ph_label, ph_order, ph_desc in STANDARD_PHASES:
            is_cur = 1 if ph_id == current_phase else 0
            v_count = 2 if ph_id == current_phase and proj_id == "proj-test-001" else (1 if ph_id == current_phase else 0)
            r_count = v_count
            phase_rows.append((
                proj_id, ph_id, ph_label, ph_order, ph_desc,
                iso(14) if is_cur else "", "", is_cur, v_count, r_count,
            ))
    db.executemany(
        """INSERT OR REPLACE INTO phases
           (project_id, phase_id, label, phase_order, description,
            entered_at, exited_at, is_current, version_count, review_count)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        phase_rows,
    )
    db.commit()
    print(f"  ✓ {len(phase_rows)} phase rows inserted")

    # ── Versions ──────────────────────────────────────────────
    included_artifacts_001 = json.dumps([
        {"filename": "scope_document.pdf", "category": "project_artefact"},
        {"filename": "client_requirements.docx", "category": "client_context"},
    ])
    included_artifacts_002 = json.dumps([
        {"filename": "architecture_design.pdf", "category": "architecture_design"},
    ])

    versions = [
        # proj-test-001 — 2 versions
        (
            "v1", "proj-test-001", "pre-sales", "Initial Scope Assessment", "Solution Architect",
            "Migrate 45 legacy workloads to AWS over 18 months. Focus on lift-and-shift for Phase 1.",
            "files_only", included_artifacts_001, "[]",
            json.dumps({"risks": 5, "assumptions": 3, "dependencies": 4, "constraints": 2, "action_items": 6}),
            json.dumps(["r1"]), "r1", iso(10),
        ),
        (
            "v2", "proj-test-001", "pre-sales", "Post-Discovery Revision", "Delivery Manager",
            "Revised scope after discovery workshop. 45 workloads confirmed, 3 decommissioned.",
            "files_only", included_artifacts_001, "[]",
            json.dumps({"risks": 3, "assumptions": 5, "dependencies": 6, "constraints": 2, "action_items": 4}),
            json.dumps(["r2"]), "r2", iso(3),
        ),
        # proj-test-002 — 1 version
        (
            "v1", "proj-test-002", "delivery", "Sprint 4 Checkpoint", "Product Owner",
            "Digital transformation sprint 4 — CRM integration milestone reached.",
            "files_only", included_artifacts_002, "[]",
            json.dumps({"risks": 2, "assumptions": 1, "dependencies": 3, "constraints": 1, "action_items": 2}),
            json.dumps(["r1"]), "r1", iso(5),
        ),
    ]
    db.executemany(
        """INSERT OR REPLACE INTO versions
           (version_id, project_id, phase_id, label, persona, scope, ai_backend,
            included_artifacts, excluded_artifacts, stats, review_ids, active_review_id, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        versions,
    )
    db.commit()
    print(f"  ✓ {len(versions)} versions inserted")

    # ── Reviews ───────────────────────────────────────────────
    findings_001_r1 = json.dumps({
        "risks": [
            "Data sovereignty compliance for EU customer data during migration window",
            "Network latency spikes during cutover affecting real-time transactions",
            "Vendor lock-in risk with AWS proprietary services",
            "Skill gap in DevOps team for Kubernetes workload management",
            "Undocumented legacy integrations discovered post-assessment",
        ],
        "assumptions": [
            "AWS Direct Connect provisioned before migration start",
            "All application owners available during UAT window",
            "Zero-downtime migration approved by client stakeholders",
        ],
        "dependencies": [
            "AWS Direct Connect circuit (8-week lead time)",
            "Legacy ERP vendor co-operation for data export",
            "Security team sign-off on VPC peering design",
            "Network team VLAN reconfiguration (sprint -2)",
        ],
        "constraints": [
            "Migration must complete before Q4 financial year-end freeze",
            "No changes to production ERP during migration window",
        ],
        "action_items": [
            "Confirm AWS region selection with CISO",
            "Schedule discovery workshop for undocumented integrations",
            "Obtain Direct Connect quote from AWS account team",
            "Draft risk register and share with client PMO",
            "Agree cutover window with operations team",
            "Validate DR runbook with platform team",
        ],
    })
    findings_001_r2 = json.dumps({
        "risks": [
            "Data sovereignty compliance for EU customer data during migration window",
            "Skill gap in DevOps team for Kubernetes workload management",
            "Undocumented legacy integrations discovered post-assessment",
        ],
        "assumptions": [
            "AWS Direct Connect provisioned before migration start",
            "All application owners available during UAT window",
            "Zero-downtime migration approved by client stakeholders",
            "3 decommissioned workloads confirmed by application owners",
            "Phase 2 re-platforming budget approved separately",
        ],
        "dependencies": [
            "AWS Direct Connect circuit (8-week lead time)",
            "Legacy ERP vendor co-operation for data export",
            "Security team sign-off on VPC peering design",
            "Network team VLAN reconfiguration",
            "Application owner sign-off on decommission list",
            "DR environment provisioned in eu-west-2",
        ],
        "constraints": [
            "Migration must complete before Q4 financial year-end freeze",
            "No changes to production ERP during migration window",
        ],
        "action_items": [
            "Confirm AWS region selection with CISO",
            "Validate DR runbook with platform team",
        ],
        "recommendations": [
            "Consider FinOps review after Phase 1 completion",
            "Introduce tagging strategy before workload migration",
            "Establish CloudWatch baseline before cutover",
            "Negotiate AWS Enterprise Support tier before go-live",
        ],
    })
    findings_002_r1 = json.dumps({
        "risks": [
            "CRM integration API rate limits may cause data sync delays",
            "Change fatigue across business units slowing adoption",
        ],
        "assumptions": ["Business units will complete UAT within 2-week window"],
        "dependencies": [
            "CRM vendor API sandbox access",
            "Identity provider SSO configuration",
            "Data migration scripts validated against production snapshot",
        ],
        "constraints": ["Go-live must not conflict with Q3 board reporting period"],
        "action_items": [
            "Resolve CRM API rate limit issue with vendor",
            "Schedule change management sessions with each BU",
        ],
    })

    reviews = [
        (
            "r1", "proj-test-001", "v1", "pre-sales", "Solution Architect", "files_only",
            "Review scope and identify key risks for the AWS migration programme.",
            "", "{}", findings_001_r1, "[]",
            "Initial assessment identifies 5 risks and 4 dependencies. Critical path items are Direct Connect provisioning and ERP vendor co-operation.",
            json.dumps(["scope_document.pdf", "client_requirements.docx"]),
            json.dumps(["project_artefact", "client_context"]),
            "{}", None, None, iso(10),
        ),
        (
            "r2", "proj-test-001", "v2", "pre-sales", "Delivery Manager", "files_only",
            "Post-discovery revision review. Validate scope changes and updated risk profile.",
            "", "{}", findings_001_r2, "[]",
            "Risk count reduced from 5 to 3 after discovery workshop. 4 new recommendations added. Scope confirmed at 42 workloads.",
            json.dumps(["scope_document.pdf", "client_requirements.docx"]),
            json.dumps(["project_artefact", "client_context"]),
            "{}", None, None, iso(3),
        ),
        (
            "r1", "proj-test-002", "v1", "delivery", "Product Owner", "files_only",
            "Sprint 4 delivery checkpoint review.",
            "", "{}", findings_002_r1, "[]",
            "Sprint 4 on track. CRM integration 80% complete. 2 risks active, 1 action required with vendor.",
            json.dumps(["architecture_design.pdf"]),
            json.dumps(["architecture_design"]),
            "{}", None, None, iso(5),
        ),
    ]
    # Map project_id for composite PK
    review_rows_proj1 = [r for r in reviews if r[1] == "proj-test-001"]
    review_rows_proj2 = [r for r in reviews if r[1] == "proj-test-002"]

    db.executemany(
        """INSERT OR REPLACE INTO reviews
           (review_id, project_id, version_id, phase_id, persona, ai_backend,
            prompt_used, custom_prompt, output, findings, questions, summary,
            included_files, categories, ai_metadata, deep_dive, feedback, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        reviews,
    )
    db.commit()
    print(f"  ✓ {len(reviews)} reviews inserted")

    # ── Artifacts ─────────────────────────────────────────────
    artifacts = [
        (
            "a_seed001", "proj-test-001", "file", "scope_document.pdf",
            "Cloud Migration Scope Document", "project_artefact",
            json.dumps({"version": "1.2", "owner": "Programme Manager"}),
            1, "processed", "", "", iso(13),
        ),
        (
            "a_seed002", "proj-test-002", "file", "architecture_design.pdf",
            "Target Architecture Design", "architecture_design",
            json.dumps({"systemName": "Digital Platform", "layer": "platform"}),
            1, "processed", "", "", iso(28),
        ),
    ]
    db.executemany(
        """INSERT OR REPLACE INTO artifacts
           (artifact_id, project_id, type, file_name, title, category,
            metadata, include, status, raw_path, text_content, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        artifacts,
    )
    db.commit()
    print(f"  ✓ {len(artifacts)} artifacts inserted")

    # ── Proposals ─────────────────────────────────────────────
    db.execute(
        """INSERT OR REPLACE INTO proposals
           (project_id, proposal_name, client, current_version,
            total_versions, created_at, updated_at)
           VALUES (?,?,?,?,?,?,?)""",
        ("proj-test-001", "AWS Cloud Migration Proposal",
         "Acme Financial Services", "prop-v2", 2, iso(12), iso(2)),
    )
    proposal_versions = [
        (
            "prop-v1", "proj-test-001", 1, "Initial Submission", "submitted",
            json.dumps(["scope_document.pdf"]),
            "First draft submitted after initial discovery call.",
            "", "v1",
            json.dumps({
                "accepted": ["Migration phased approach", "AWS as primary cloud provider"],
                "rejected": ["Full re-platform in Phase 1"],
                "concerns": ["Timeline too aggressive — Q4 freeze conflict"],
                "notes": "Client requested revised timeline before proceeding.",
                "captured_at": iso(8),
            }),
            iso(12),
        ),
        (
            "prop-v2", "proj-test-001", 2, "Post-Feedback Revision", "under_review",
            json.dumps(["scope_document.pdf", "client_requirements.docx"]),
            "Revised proposal addressing client timeline concern. Phase 1 extended by 6 weeks.",
            "Extended Phase 1 timeline, removed re-platform scope, added FinOps review milestone.",
            "v2", None, iso(2),
        ),
    ]
    db.executemany(
        """INSERT OR REPLACE INTO proposal_versions
           (version_id, project_id, version_number, label, status,
            files, notes, changes_from_previous, context_version,
            feedback, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        proposal_versions,
    )
    db.commit()
    print("  ✓ 1 proposal + 2 versions inserted")

    # ── Pre-sales feedback ─────────────────────────────────────
    db.execute(
        """INSERT OR REPLACE INTO presales_feedback
           (feedback_id, project_id, proposal_ver_id, review_id, source,
            responder_name, responder_email, accepted, rejected, concerns,
            notes, next_action, status, created_at, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            "fb_seed001", "proj-test-001", "prop-v1", "r1", "internal",
            "Sarah Chen", "s.chen@acmefinancial.com",
            json.dumps(["Migration phased approach", "AWS as primary cloud provider"]),
            json.dumps(["Full re-platform in Phase 1"]),
            json.dumps(["Timeline too aggressive — Q4 freeze conflict",
                        "Need dedicated security review before sign-off"]),
            "Client happy with overall direction but needs timeline revision before board sign-off.",
            "Revise proposal timeline, schedule security review session.",
            "actioned", iso(8), iso(2),
        ),
    )
    db.commit()
    print("  ✓ 1 presales feedback entry inserted")

    # ── Mirror to JSON files ───────────────────────────────────
    _mirror_to_files()

    print("\n✅ Seed complete. DB:", db.path)
    print("   Projects: proj-test-001 (pre-sales), proj-test-002 (delivery)")


def _mirror_to_files() -> None:
    """Write JSON file mirrors so the app works even with file_write_enabled=True."""
    from db.project_store_sql import _rebuild_projects_file, _rebuild_proposal_file, load_projects_sql
    from db.artifact_store_sql import _rebuild_registry_file
    from db.hierarchy_store_sql import HierarchyStoreSQLite

    _rebuild_projects_file()
    print("  ✓ projects.json written")

    _rebuild_registry_file("proj-test-001")
    _rebuild_registry_file("proj-test-002")
    print("  ✓ artifacts.json written for both projects")

    # Rebuild hierarchy files
    for pid in ("proj-test-001", "proj-test-002"):
        store = HierarchyStoreSQLite(pid)
        store._file_seed_phases()
        vers = store.list_versions()
        for v in vers:
            ver_obj = store.get_version(v["version_id"])
            if ver_obj:
                store._file_save_version(ver_obj)
        revs = store.list_reviews()
        for r in revs:
            rev_obj = store.get_review(r["review_id"])
            if rev_obj:
                store._file_save_review(rev_obj)
    print("  ✓ hierarchy JSON files written for both projects")

    _rebuild_proposal_file("proj-test-001")
    print("  ✓ proposals/tracker.json written for proj-test-001")


if __name__ == "__main__":
    run()
