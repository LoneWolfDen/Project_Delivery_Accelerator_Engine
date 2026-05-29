#!/usr/bin/env python3
"""seed_demo.py – Populate the application with 3 realistic demo projects.

Run from the project root:
    python scripts/seed_demo.py

Creates:
  1. Healthcare Cloud Migration Assessment  (3 versions, 2 reviews each)
  2. Retail Digital Commerce Platform SoW   (2 versions, 1 review each)
  3. Internal DevEx Platform (pre-sales)     (1 version,  1 review)

Wipes existing projects_data first (ask for confirmation).
"""

import json
import sys
import shutil
from pathlib import Path

# ── Bootstrap: add project root to sys.path ──────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import project_manager
from processors.history import save_context_version
from models.hierarchy import HierarchyStore

WIPE_PROMPT = True  # Set False to skip the confirmation prompt

# ─────────────────────────────────────────────────────────────────────────────
# Artefact text content – realistic but concise
# ─────────────────────────────────────────────────────────────────────────────

HEALTH_SCOPE = """
AnyHealth NHS Trust – Cloud Migration Scope of Work

OBJECTIVES
Migrate 18 clinical applications from on-premises VMware to AWS (Ireland region).
Target completion: 18 months. Budget: £4.2M.

KEY DELIVERABLES
1. Application discovery & dependency mapping (Month 1-2)
2. AWS Landing Zone + network topology (Month 2-3)
3. Lift-and-shift for Tier-2/3 apps (Month 3-8)
4. Re-platform EHR and Patient Portal to containerised architecture (Month 8-14)
5. Data migration (800TB Oracle + PostgreSQL) with zero data loss guarantee
6. Disaster Recovery to EU-West-2 with RTO <4h, RPO <1h
7. HIPAA & NHS DSPT compliance sign-off
8. Cutover & hypercare (Month 16-18)

RISKS
- Key person dependency: only 2 FHIR integration engineers available
- Third-party EHR vendor (Epic) upgrade dependency blocking re-platform
- 24/7 clinical operations – zero-downtime migration required
- NHS procurement approval cycle adds 6-week lead time per vendor
- Budget contingency not yet approved by Board

ASSUMPTIONS
- AWS Direct Connect provisioned by network team before Month 2
- Epic vendor will respond to API schema queries within 2 weeks
- Clinical staff available for UAT in Month 13-14
- HIPAA BAA signed with AWS before data migration starts

DEPENDENCIES
- NHS Digital Data Dictionary v3.2 compliance
- HL7 FHIR R4 interface readiness from 3 third-party systems
- Existing AD/LDAP directory remains authoritative for identity

STAKEHOLDERS
- Sponsor: CTO – Dr. Sarah Ahmed
- Clinical Owner: Chief Medical Officer
- IT Lead: Head of Infrastructure
- Vendor: AWS Professional Services

CONSTRAINTS
- HIPAA, NHS DSPT, CQC regulatory compliance mandatory
- All PII must remain within UK/EU data residency
- No maintenance windows during core clinical hours 08:00-20:00
- Legacy COBOL billing system cannot be migrated until FY2026

ACTION ITEMS
- Confirm AWS Direct Connect delivery date with network team
- Schedule HIPAA risk assessment with compliance officer
- Obtain Epic vendor commitment letter for API access
- Board approval for contingency budget (£420K)
"""

HEALTH_RISKS_CSV = """risk_id,description,severity,probability,mitigation
R001,Key-person dependency on FHIR engineers,High,High,Hire second FHIR contractor by Month 1
R002,Epic EHR vendor upgrade blocking re-platform,High,Medium,Agree freeze window contractually
R003,Zero-downtime cutover for 24x7 clinical ops,Critical,Medium,Blue-green deployment with 30-day parallel run
R004,Budget overrun due to data migration complexity,High,Low,Monthly cost reviews with AWS cost explorer
R005,HIPAA BAA not signed before data transfer,Critical,Low,Legal team to expedite – hard gate at Month 2
R006,NHS procurement 6-week delay,Medium,High,Pre-approve vendor shortlist in Month 1
R007,AWS Direct Connect provisioning delay,Medium,Medium,Order in Week 1; backup VPN path as fallback
"""

HEALTH_MEETING = """
Meeting Notes – Cloud Migration Steering Committee
Date: 2026-03-15 | Attendees: CTO, CMO, Head of Infra, AWS PS Lead

DECISIONS
1. Approved Phase 1 scope (discovery + landing zone) to proceed
2. AWS Ireland selected as primary region; Dublin DR site confirmed
3. Epic vendor engagement to begin immediately

ACTION ITEMS
- Dr. Ahmed to escalate Epic API access to Epic account executive
- Head of Infra to confirm Direct Connect order by 2026-03-22
- AWS PS to deliver HIPAA readiness assessment by 2026-04-01
- Programme office to publish RAID log by 2026-03-20

RISKS RAISED
- CMO flagged concern about clinical staff availability for UAT in Month 13
- Head of Infra warned that VMware licensing expires Month 10 – potential cost overrun

NEXT MEETING: 2026-04-05
"""

# ─────────────────────────────────────────────────────────────────────────────

RETAIL_SCOPE = """
RetailCo – Digital Commerce Platform – Statement of Work

OBJECTIVES
Deliver a next-generation e-commerce platform replacing the 12-year-old monolith.
Target: 10M concurrent users at peak. Go-live: Q4 2026. Budget: €6.8M.

KEY DELIVERABLES
1. Microservices architecture (product catalogue, basket, checkout, payments, notifications)
2. React/Next.js frontend with sub-1s page load (Core Web Vitals green)
3. Personalisation engine (ML-based recommendations)
4. Integration with SAP ERP, Adyen payments, Salesforce CRM
5. GDPR-compliant data layer with cookie consent
6. Global CDN rollout (EU, US, APAC)
7. Load tested to 10M concurrent users

RISKS
- SAP ERP integration complexity – custom ABAP modules not documented
- Peak traffic (Black Friday) 40x normal load – infrastructure cost unpredictable
- Product catalogue migration: 2.3M SKUs with variant logic
- Personalisation model training requires 18 months of historic data
- Team skill gap in Kubernetes/GitOps – training plan not yet agreed

ASSUMPTIONS
- Adyen API documentation and sandbox credentials available Week 1
- Historic order data export from legacy system ready by Month 2
- SAP technical team available 3 days/week for integration work
- Marketing team signs off UX wireframes within 2 weeks of delivery

DEPENDENCIES
- Adyen payment gateway certification (PCI DSS)
- SAP S/4 HANA upgrade (planned Month 3) – interface freeze needed
- Cloudflare contract renewal for CDN

STAKEHOLDERS
- Sponsor: Chief Digital Officer
- Product Owner: Head of E-Commerce
- Technical Lead: VP Engineering
- Vendor: Adyen, SAP, Cloudflare

CONSTRAINTS
- GDPR/CCPA compliance mandatory
- PCI DSS Level 1 for payment handling
- Zero downtime cutover from legacy platform
- Existing mobile app must continue working during migration (API compatibility)

ACTION ITEMS
- Obtain Adyen sandbox credentials from procurement
- Schedule SAP ABAP documentation workshop with SAP team
- Agree UAT entry criteria with Head of E-Commerce
- Commission Black Friday load test plan
"""

RETAIL_DESIGN_DOC = """
Digital Commerce Platform – Architecture Decision Record

ADR-001: Microservices vs Modular Monolith
Decision: Microservices (12 bounded contexts)
Rationale: Scale, independent deployment, team autonomy
Risks: Distributed systems complexity, latency overhead

ADR-002: Frontend Framework
Decision: Next.js 14 (App Router)
Rationale: SSR for SEO, React ecosystem, Vercel edge deployment

ADR-003: Database Strategy
Decision: PostgreSQL (transactional), Redis (cache), Elasticsearch (search)
Rationale: Open source, proven at scale, no vendor lock-in

ADR-004: API Gateway
Decision: Kong Gateway (OSS)
Rationale: Rate limiting, auth, observability – open source aligned with constraints

NON-FUNCTIONAL REQUIREMENTS
- Page load: P95 < 1s (CDN-cached), P95 < 3s (origin)
- Availability: 99.95% uptime (4.4h downtime/year)
- Data residency: EU primary, US replicated
- Security: OWASP Top 10, PCI DSS Level 1, GDPR Article 25

SECURITY ARCHITECTURE
- OAuth 2.0 / OIDC via Keycloak (open source IdP)
- All PII encrypted at rest (AES-256) and in transit (TLS 1.3)
- WAF in front of all public endpoints
- Secrets managed via HashiCorp Vault
"""

# ─────────────────────────────────────────────────────────────────────────────

DEVEX_SCOPE = """
InternalCo – Developer Experience (DevEx) Platform – Pre-Sales Brief

OBJECTIVES
Reduce developer onboarding from 3 weeks to 2 days.
Standardise CI/CD, observability, and self-service infrastructure for 120 engineers.
Budget estimate: £1.8M over 18 months.

PROPOSED SOLUTION
1. Internal Developer Portal (Backstage OSS)
2. Golden-path CI/CD templates (GitHub Actions + ArgoCD)
3. Self-service infrastructure provisioning (Terraform + Atlantis)
4. Unified observability stack (Prometheus, Grafana, OpenTelemetry)
5. Service catalogue with auto-populated docs

RISKS
- Backstage adoption requires significant engineer behaviour change
- Existing 47 heterogeneous pipelines must be migrated without breaking them
- No dedicated platform team yet – relying on embedded champions
- Terraform state management for 300+ existing resources is a large migration
- Leadership buy-in at team-lead level is not yet confirmed

ASSUMPTIONS
- 2 platform engineers dedicated full-time from start
- GitHub Enterprise is the agreed SCM (no migration needed)
- Teams will adopt golden paths voluntarily (incentive model TBD)

STAKEHOLDERS
- Sponsor: VP Engineering
- Champion: Principal Engineer
- Affected teams: 12 product squads

CONSTRAINTS
- Must be open source (no SaaS vendor lock-in)
- Existing cloud spend budget does not increase
- Platform team cannot disrupt ongoing product delivery

ACTION ITEMS
- Confirm platform team headcount with VP Engineering
- Survey 3 pilot squads for pain points
- Prototype Backstage with 1 sample service by end of Month 1
"""


# ─────────────────────────────────────────────────────────────────────────────
# Minimal synthetic context dicts (pre-built – no need to call build_context)
# This lets us create rich demo data without needing AI or file ingestion.
# ─────────────────────────────────────────────────────────────────────────────

def _build_context_v1_health():
    return {
        "scope": HEALTH_SCOPE.strip(),
        "risks": [
            "Key-person dependency on FHIR engineers – only 2 available",
            "Epic EHR vendor upgrade blocking re-platform schedule",
            "Zero-downtime cutover required for 24x7 clinical operations",
            "Budget contingency not yet approved by Board",
            "NHS procurement 6-week approval cycle per vendor",
            "AWS Direct Connect provisioning could delay Month 2 start",
            "HIPAA BAA must be signed before any data transfer begins",
        ],
        "assumptions": [
            "AWS Direct Connect provisioned before Month 2",
            "Epic vendor responds to API queries within 2 weeks",
            "Clinical staff available for UAT in Month 13–14",
            "HIPAA BAA signed with AWS before data migration starts",
        ],
        "dependencies": [
            "NHS Digital Data Dictionary v3.2 compliance",
            "HL7 FHIR R4 readiness from 3 third-party systems",
            "Existing AD/LDAP directory for identity",
            "Epic vendor API access agreement",
        ],
        "constraints": [
            "HIPAA, NHS DSPT, CQC regulatory compliance mandatory",
            "All PII must remain within UK/EU data residency",
            "No maintenance windows during core clinical hours 08:00–20:00",
            "Legacy COBOL billing system cannot migrate until FY2026",
            "Budget cap: £4.2M plus pending £420K contingency",
        ],
        "action_items": [
            "Confirm AWS Direct Connect delivery date with network team",
            "Schedule HIPAA risk assessment with compliance officer",
            "Obtain Epic vendor commitment letter for API access",
            "Board approval for contingency budget (£420K)",
        ],
        "resources": [{"description": "AWS Professional Services team"}, {"description": "FHIR integration engineers (x2)"}],
        "summary": "Context built from 3 documents. 7 risks, 4 assumptions, 4 dependencies, 5 constraints, 4 action items.",
        "_build_metadata": {
            "built_at": "2026-04-10T09:00:00+00:00",
            "document_count": 3, "valid_documents": 3,
            "total_risks": 7, "total_assumptions": 4,
            "total_dependencies": 4, "total_constraints": 5, "total_action_items": 4,
        },
    }


def _build_context_v2_health():
    ctx = _build_context_v1_health()
    ctx["risks"] = ctx["risks"] + [
        "Parallel-run period cost may exceed £120K AWS estimate",
        "Consent management module scope creep from legal team",
    ]
    ctx["assumptions"] = ctx["assumptions"] + [
        "Blue-green deployment infrastructure approved by security team",
    ]
    ctx["action_items"] = ctx["action_items"] + [
        "Confirm parallel-run infrastructure cost with AWS",
        "Legal team to finalise consent management scope",
    ]
    ctx["_build_metadata"] = {
        "built_at": "2026-05-20T14:30:00+00:00",
        "document_count": 4, "valid_documents": 4,
        "total_risks": len(ctx["risks"]), "total_assumptions": len(ctx["assumptions"]),
        "total_dependencies": len(ctx["dependencies"]),
        "total_constraints": len(ctx["constraints"]),
        "total_action_items": len(ctx["action_items"]),
    }
    ctx["summary"] = f"Context built from 4 documents. {len(ctx['risks'])} risks, {len(ctx['assumptions'])} assumptions."
    return ctx


def _build_context_v3_health():
    ctx = _build_context_v2_health()
    # v3: some risks resolved
    ctx["risks"] = [r for r in ctx["risks"] if "Direct Connect" not in r and "procurement" not in r]
    ctx["risks"].append("Hypercare resource allocation not yet confirmed post go-live")
    ctx["action_items"] = [a for a in ctx["action_items"] if "Direct Connect" not in a]
    ctx["action_items"].append("Confirm hypercare team with resourcing manager")
    ctx["_build_metadata"] = {
        "built_at": "2026-06-15T10:00:00+00:00",
        "document_count": 5, "valid_documents": 5,
        "total_risks": len(ctx["risks"]), "total_assumptions": len(ctx["assumptions"]),
        "total_dependencies": len(ctx["dependencies"]),
        "total_constraints": len(ctx["constraints"]),
        "total_action_items": len(ctx["action_items"]),
    }
    ctx["summary"] = f"Context built from 5 documents. {len(ctx['risks'])} risks (2 resolved)."
    return ctx


def _build_context_v1_retail():
    return {
        "scope": RETAIL_SCOPE.strip(),
        "risks": [
            "SAP ERP integration complexity – ABAP modules undocumented",
            "Black Friday 40x traffic spike – infrastructure cost unpredictable",
            "2.3M SKU catalogue migration with complex variant logic",
            "Personalisation model requires 18 months of historic data",
            "Kubernetes/GitOps skill gap in engineering team",
        ],
        "assumptions": [
            "Adyen API sandbox credentials available Week 1",
            "Historic order data export from legacy system ready by Month 2",
            "SAP technical team available 3 days/week",
            "Marketing team signs off wireframes within 2 weeks",
        ],
        "dependencies": [
            "Adyen PCI DSS certification",
            "SAP S/4 HANA interface freeze during Month 3 upgrade",
            "Cloudflare CDN contract renewal",
        ],
        "constraints": [
            "GDPR/CCPA compliance mandatory",
            "PCI DSS Level 1 for payment handling",
            "Zero downtime cutover from legacy platform",
            "Existing mobile app API compatibility during migration",
            "Budget: €6.8M",
        ],
        "action_items": [
            "Obtain Adyen sandbox credentials from procurement",
            "Schedule SAP ABAP documentation workshop",
            "Agree UAT entry criteria with Head of E-Commerce",
            "Commission Black Friday load test plan",
        ],
        "resources": [{"description": "VP Engineering"}, {"description": "3 senior backend engineers (microservices)"}],
        "summary": "Context from 2 documents. 5 risks, 4 assumptions, 3 dependencies, 5 constraints.",
        "_build_metadata": {
            "built_at": "2026-03-01T11:00:00+00:00",
            "document_count": 2, "valid_documents": 2,
            "total_risks": 5, "total_assumptions": 4,
            "total_dependencies": 3, "total_constraints": 5, "total_action_items": 4,
        },
    }


def _build_context_v2_retail():
    ctx = _build_context_v1_retail()
    ctx["risks"] = ctx["risks"] + [
        "Security penetration test timeline not yet scheduled",
        "Keycloak IdP integration with legacy user database not prototyped",
    ]
    ctx["assumptions"].append("Keycloak can federate with existing LDAP within 2 sprints")
    ctx["_build_metadata"] = {
        "built_at": "2026-04-18T09:00:00+00:00",
        "document_count": 3, "valid_documents": 3,
        "total_risks": len(ctx["risks"]), "total_assumptions": len(ctx["assumptions"]),
        "total_dependencies": len(ctx["dependencies"]),
        "total_constraints": len(ctx["constraints"]),
        "total_action_items": len(ctx["action_items"]),
    }
    ctx["summary"] = f"Context from 3 documents. {len(ctx['risks'])} risks."
    return ctx


def _build_context_v1_devex():
    return {
        "scope": DEVEX_SCOPE.strip(),
        "risks": [
            "Backstage adoption requires significant engineering behaviour change",
            "47 heterogeneous pipelines must migrate without breaking product delivery",
            "No dedicated platform team yet – relying on embedded champions",
            "Terraform state migration for 300+ existing resources is high-risk",
            "Leadership buy-in at team-lead level not confirmed",
        ],
        "assumptions": [
            "2 platform engineers dedicated full-time from project start",
            "GitHub Enterprise is agreed SCM – no migration needed",
            "Teams will adopt golden paths voluntarily",
        ],
        "dependencies": [
            "GitHub Enterprise license renewal",
            "Cloud team approval for ArgoCD cluster access",
        ],
        "constraints": [
            "Must be 100% open source (no SaaS vendor lock-in)",
            "Existing cloud spend must not increase",
            "Platform team cannot disrupt ongoing product delivery",
        ],
        "action_items": [
            "Confirm platform team headcount with VP Engineering",
            "Survey 3 pilot squads for pain points",
            "Prototype Backstage with 1 sample service by end of Month 1",
        ],
        "resources": [{"description": "2 x Platform Engineer (FTE)"}, {"description": "Principal Engineer (part-time champion)"}],
        "summary": "Context from 1 document. 5 risks, 3 assumptions, 2 dependencies.",
        "_build_metadata": {
            "built_at": "2026-05-01T08:30:00+00:00",
            "document_count": 1, "valid_documents": 1,
            "total_risks": 5, "total_assumptions": 3,
            "total_dependencies": 2, "total_constraints": 3, "total_action_items": 3,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# Review output factory
# ─────────────────────────────────────────────────────────────────────────────

def _review(persona_id, persona_name, backend, summary, findings, questions, description="", ts="2026-04-11T10:00:00+00:00"):
    return {
        "persona": persona_name,
        "persona_id": persona_id,
        "description": description,
        "timestamp": ts,
        "ai_backend": backend,
        "summary": summary,
        "findings": findings,
        "questions": questions,
        "recommendations": findings.get("recommendations", []),
        "prompt_used": f"[{persona_name} review prompt – {backend}]",
        "custom_prompt": "",
        "raw_output": None,
        "ai_metadata": {},
    }


HEALTH_REVIEW_SA_V1 = _review(
    "solution_architect", "Solution Architect", "files_only",
    "Solution Architect review: 6 findings across 3 categories",
    {
        "risks": [
            "Epic EHR vendor API schema not yet documented – blocks re-platform design",
            "Zero-downtime migration requires blue-green infra not yet costed",
            "HIPAA BAA absent – hard blocker before any PHI data transfer",
        ],
        "design_gaps": [
            "No disaster recovery runbook defined – RTO/RPO targets stated but untested",
            "HL7 FHIR R4 interface design depends on 3 third parties with no SLAs",
            "Terraform state strategy for 800TB storage migration not documented",
        ],
        "recommendations": [
            "Define architecture decision record (ADR) for DR strategy before Month 3",
            "Prototype FHIR R4 integration with Epic sandbox before committing to timeline",
            "Add HIPAA BAA as a hard gate in the project plan",
        ],
        "questions": [],
    },
    [
        "Has the Epic sandbox environment been provisioned for FHIR integration testing?",
        "What is the DR test plan and who owns it?",
        "Is encryption-at-rest verified for all 800TB storage classes?",
    ],
    description="Initial pre-sales architecture risk scan of NHS Trust migration SoW",
    ts="2026-04-11T10:00:00+00:00",
)

HEALTH_REVIEW_DM_V1 = _review(
    "delivery_manager", "Delivery Manager", "files_only",
    "Delivery Manager review: 5 findings across 2 categories",
    {
        "execution_risks": [
            "NHS procurement 6-week delay unmitigated – threatens Month 2 start",
            "Only 2 FHIR engineers available; single point of failure on critical path",
            "Board contingency approval (£420K) outstanding – budget at risk",
        ],
        "dependency_issues": [
            "Dependency: AWS Direct Connect – no confirmed delivery date",
            "Dependency: Epic vendor API access – commitment letter not received",
        ],
        "recommendations": [
            "Escalate procurement approval to CTO sponsor immediately",
            "Begin FHIR contractor recruitment now, not at Month 1 start",
        ],
        "questions": [],
    },
    [
        "Is there schedule contingency buffer built into the 18-month plan?",
        "Who owns the dependency on AWS Direct Connect provisioning?",
        "Have all dependency owners confirmed their commitments in writing?",
    ],
    description="Delivery feasibility review – checking execution risks and dependencies",
    ts="2026-04-12T14:00:00+00:00",
)

HEALTH_REVIEW_SA_V2 = _review(
    "solution_architect", "Solution Architect", "groq",
    "Solution Architect review: 4 findings (2 risks resolved vs v1)",
    {
        "risks": [
            "Parallel-run cost may exceed budget – no AWS cost ceiling agreed",
            "Consent management scope not yet finalised with legal team",
        ],
        "design_gaps": [
            "Blue-green deployment architecture now drafted but not reviewed by security",
        ],
        "recommendations": [
            "Set AWS cost alert at 80% of parallel-run budget allocation",
            "Security team review of blue-green architecture before Month 8",
        ],
        "questions": [],
    },
    [
        "Has the security team signed off the blue-green deployment architecture?",
        "What is the rollback trigger criteria during the 30-day parallel run?",
    ],
    description="Post-discovery update – 2 risks resolved, 2 new scope items raised by legal",
    ts="2026-05-22T11:00:00+00:00",
)

HEALTH_REVIEW_DM_V2 = _review(
    "delivery_manager", "Delivery Manager", "groq",
    "Delivery Manager review: Dependency risk improved, scope risk increased",
    {
        "execution_risks": [
            "Legal consent management scope creep threatens Month 14 deadline",
            "Parallel-run resource allocation not yet confirmed with resourcing team",
        ],
        "dependency_issues": [
            "Direct Connect delivery confirmed – dependency resolved ✓",
        ],
        "recommendations": [
            "Raise formal change request for consent management scope",
            "Confirm hypercare team allocation with resourcing manager by Month 12",
        ],
        "questions": [],
    },
    [
        "Has the change control board reviewed the consent management scope addition?",
        "Is the parallel-run cost within the approved budget?",
    ],
    description="Mid-project health check – dependencies improved, scope risk increasing",
    ts="2026-05-23T09:30:00+00:00",
)

RETAIL_REVIEW_SA = _review(
    "solution_architect", "Solution Architect", "files_only",
    "Solution Architect review: 5 architecture findings",
    {
        "risks": [
            "SAP ABAP integration complexity – undocumented modules are a black box",
            "Microservices latency budget not defined – 12 services risk SLA breach",
        ],
        "design_gaps": [
            "No API contract testing strategy for 12 microservices",
            "PCI DSS scope boundary not drawn – unclear which services are in-scope",
            "Keycloak federation with legacy LDAP user database not prototyped",
        ],
        "recommendations": [
            "Define API contracts (OpenAPI 3.0) before sprint 1 of each bounded context",
            "Engage QSA for PCI DSS scoping workshop in Month 1",
            "Prototype Keycloak-LDAP federation as a spike in Month 1",
        ],
        "questions": [],
    },
    [
        "What is the end-to-end latency budget for checkout (SAP → basket → payment)?",
        "Which microservices are in PCI DSS scope?",
        "Is there a WAF strategy for the new platform?",
    ],
    description="Architecture review of Digital Commerce Platform SoW v1",
    ts="2026-03-05T10:00:00+00:00",
)

RETAIL_REVIEW_PO = _review(
    "product_owner", "Product Owner", "files_only",
    "Product Owner review: scope and value alignment findings",
    {
        "scope_gaps": [
            "No explicit acceptance criteria defined for personalisation engine",
            "Mobile app API compatibility scope is vague – 'continue working' is not testable",
            "Black Friday performance SLA (10M concurrent users) needs load test sign-off criteria",
        ],
        "backlog_quality_issues": [
            "2.3M SKU migration: no definition of done for data quality validation",
            "GDPR consent management feature: no user story defined",
        ],
        "recommendations": [
            "Define measurable acceptance criteria for personalisation: CTR uplift target",
            "Write mobile API compatibility test suite before cutover",
        ],
        "questions": [],
    },
    [
        "What is the business value metric for the personalisation engine (CTR, conversion)?",
        "Who signs off the mobile app compatibility test results?",
        "Is GDPR consent management in scope for go-live or post-launch?",
    ],
    description="Product Owner pre-project review – scope clarity and value alignment check",
    ts="2026-03-06T15:00:00+00:00",
)

DEVEX_REVIEW_SA = _review(
    "solution_architect", "Solution Architect", "files_only",
    "Solution Architect review: 4 platform architecture findings",
    {
        "risks": [
            "Terraform state migration for 300+ resources is high-risk without a dry-run",
            "Backstage plugin ecosystem maturity varies – 3rd-party plugins may be unsupported",
        ],
        "design_gaps": [
            "Observability stack (Prometheus/Grafana) retention and alerting policy not defined",
            "No multi-tenancy model for Backstage – all 12 squads sharing one instance",
        ],
        "recommendations": [
            "Run Terraform state migration in staging environment first with 10 sample resources",
            "Define Backstage RBAC model before onboarding first pilot squad",
            "Set observability retention policy: 15 days hot, 1 year cold (object storage)",
        ],
        "questions": [],
    },
    [
        "Is there a GitOps rollback strategy if ArgoCD sync causes an incident?",
        "How will secret rotation be handled across 12 squads using Vault?",
        "What is the platform team's on-call responsibility for golden-path CI/CD?",
    ],
    description="Pre-sales architecture sanity check for internal DevEx platform proposal",
    ts="2026-05-05T09:00:00+00:00",
)


# ─────────────────────────────────────────────────────────────────────────────
# Seeder core
# ─────────────────────────────────────────────────────────────────────────────

def wipe_data():
    data_dir = project_manager.PROJECTS_DIR
    if data_dir.exists():
        shutil.rmtree(data_dir)
        print(f"  Wiped {data_dir}")
    data_dir.mkdir(parents=True, exist_ok=True)


def create_project_with_data(name, description, phase, documents, versions, reviews_per_version):
    """Create a project, write context files, create hierarchy versions and reviews."""
    print(f"\n→ Creating project: {name}")

    # Create project record
    proj = project_manager.create_project(name=name, description=description)
    pid = proj["id"]
    project_dir = project_manager.PROJECTS_DIR / pid

    # Write artefact files to context/ directory (legacy ingestion path)
    context_dir = project_dir / "context"
    context_dir.mkdir(exist_ok=True)
    for fname, content_text in documents.items():
        import json as _json
        doc = {
            "filename": fname,
            "is_valid": True,
            "sections": [{"title": "Main", "heading": "Main", "content": content_text[:2000]}],
            "metadata": {"source_type": "plain_text", "word_count": len(content_text.split()), "filename": fname},
        }
        (context_dir / fname).with_suffix(".json").write_text(_json.dumps(doc, indent=2))

    # Write versions + reviews into hierarchy
    store = HierarchyStore(pid)

    for i, (ctx, rev_list) in enumerate(zip(versions, reviews_per_version), start=1):
        # Save legacy version snapshot
        version_meta = save_context_version(project_dir, ctx, version_label=ctx.get("_label", f"Build #{i}"))
        vid = version_meta["version_id"]

        # Write current intelligence
        (project_dir / "intelligence").mkdir(exist_ok=True)
        import json as _json
        (project_dir / "intelligence" / "current.json").write_text(_json.dumps(ctx, indent=2))
        (project_dir / "intelligence.json").write_text(_json.dumps(ctx, indent=2))

        # Create hierarchy version
        included = [{"filename": k, "category": "project_artefact"} for k in documents.keys()]
        h_version = store.create_version(
            included_artifacts=included,
            label=ctx.get("_label", f"Version {i}"),
            stats=version_meta.get("stats", {}),
        )

        # Create hierarchy reviews
        for rev_data in rev_list:
            import json as _json
            rev_obj = store.create_review(
                version_id=h_version.version_id,
                persona=rev_data["persona"],
                ai_backend=rev_data["ai_backend"],
                prompt_used=rev_data.get("prompt_used", ""),
                custom_prompt=rev_data.get("custom_prompt", ""),
                output={},
                findings=rev_data.get("findings", {}),
                questions=rev_data.get("questions", []),
                summary=rev_data.get("summary", ""),
                included_files=list(documents.keys()),
                categories=["project_artefact", "plain_text"],
                ai_metadata=rev_data.get("ai_metadata", {}),
            )
            # Patch description and timestamp into the stored file
            rev_file = store.base_dir / "reviews" / f"{rev_obj.review_id}.json"
            if rev_file.exists():
                stored = _json.loads(rev_file.read_text())
                stored["description"] = rev_data.get("description", "")
                stored["created_at"] = rev_data.get("timestamp", stored["created_at"])
                rev_file.write_text(_json.dumps(stored, indent=2))

        # Also write legacy reviews/ json
        reviews_dir = project_dir / "reviews"
        reviews_dir.mkdir(exist_ok=True)
        for rev_data in rev_list:
            ts = rev_data.get("timestamp", "2026-01-01T00:00:00+00:00")
            ts_safe = ts.replace(":", "-").replace("+", "")[:19]
            fname = f"{rev_data['persona_id']}_{ts_safe}.json"
            import json as _json
            (reviews_dir / fname).write_text(_json.dumps(rev_data, indent=2))

    # Update iteration metadata
    projects = project_manager.load_projects()
    for p in projects:
        if p["id"] == pid:
            p["phase"] = phase
            p["updated_at"] = versions[-1]["_build_metadata"]["built_at"]
            break
    project_manager.save_projects(projects)

    print(f"  ✓ {pid} | {len(versions)} versions | {sum(len(r) for r in reviews_per_version)} reviews")
    return pid


def main():
    # ── Confirmation ──────────────────────────────────────────────────────────
    if WIPE_PROMPT:
        existing = project_manager.PROJECTS_DIR
        if existing.exists() and any(existing.iterdir()):
            ans = input("\n⚠ This will DELETE all existing projects_data. Continue? [y/N]: ")
            if ans.strip().lower() != "y":
                print("Aborted.")
                return

    print("\n🌱 Seeding demo data …")
    wipe_data()

    # ── Label the contexts ─────────────────────────────────────────────────────
    ctx_h1 = _build_context_v1_health(); ctx_h1["_label"] = "Initial Discovery"
    ctx_h2 = _build_context_v2_health(); ctx_h2["_label"] = "Post-Workshop Update"
    ctx_h3 = _build_context_v3_health(); ctx_h3["_label"] = "Pre-Delivery Baseline"

    ctx_r1 = _build_context_v1_retail(); ctx_r1["_label"] = "SoW v1 Analysis"
    ctx_r2 = _build_context_v2_retail(); ctx_r2["_label"] = "Architecture Review Update"

    ctx_d1 = _build_context_v1_devex(); ctx_d1["_label"] = "Pre-Sales Discovery"

    # ── Project 1: Healthcare Cloud Migration ─────────────────────────────────
    create_project_with_data(
        name="AnyHealth NHS Trust – Cloud Migration",
        description="Migration of 18 clinical applications to AWS. £4.2M, 18 months. HIPAA & NHS DSPT compliance.",
        phase="delivery",
        documents={
            "scope.txt": HEALTH_SCOPE,
            "risks.csv": HEALTH_RISKS_CSV,
            "steering_committee_notes.txt": HEALTH_MEETING,
        },
        versions=[ctx_h1, ctx_h2, ctx_h3],
        reviews_per_version=[
            [HEALTH_REVIEW_SA_V1, HEALTH_REVIEW_DM_V1],
            [HEALTH_REVIEW_SA_V2, HEALTH_REVIEW_DM_V2],
            [HEALTH_REVIEW_SA_V2],   # reuse SA v2 as final checkpoint
        ],
    )

    # ── Project 2: Retail Digital Commerce ────────────────────────────────────
    create_project_with_data(
        name="RetailCo – Digital Commerce Platform",
        description="Next-gen microservices e-commerce platform. €6.8M, Q4 2026 go-live. PCI DSS Level 1.",
        phase="design",
        documents={
            "sow.txt": RETAIL_SCOPE,
            "architecture_decisions.md": RETAIL_DESIGN_DOC,
        },
        versions=[ctx_r1, ctx_r2],
        reviews_per_version=[
            [RETAIL_REVIEW_SA, RETAIL_REVIEW_PO],
            [RETAIL_REVIEW_SA],
        ],
    )

    # ── Project 3: Internal DevEx Platform ────────────────────────────────────
    create_project_with_data(
        name="InternalCo – DevEx Platform (Pre-Sales)",
        description="Internal developer portal + golden-path CI/CD. £1.8M, 18 months. 100% open source.",
        phase="pre-sales",
        documents={
            "presales_brief.txt": DEVEX_SCOPE,
        },
        versions=[ctx_d1],
        reviews_per_version=[[DEVEX_REVIEW_SA]],
    )

    print("\n✅ Demo seed complete!")
    print("   Start the server:  python server.py")
    print("   Open browser:      http://localhost:8080")
    print()
    print("   Projects created:")
    for p in project_manager.list_projects():
        print(f"   · {p['name']} ({p['id']}) — phase: {p['phase']}")


if __name__ == "__main__":
    main()
