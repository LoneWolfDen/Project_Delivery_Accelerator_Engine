"""Runtime Protocols — structural interfaces for agentic seams (PEP 544).

Any class that satisfies a Protocol's method signatures is automatically
compatible — no inheritance required.  This keeps services decoupled from
concrete agent implementations and makes each seam mockable in tests.

Protocols defined here
----------------------
ReviewAgent
    Runs a persona review.  Implemented by the real LLM-backed engine and
    by stub/mock agents used in tests.

IntelligenceProvider
    Loads or builds project intelligence.

DeepDiveAgent
    Generates SME questions for a project context.

ProposalAgent
    Generates a proposal document from a Version + Review context.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol, Union, runtime_checkable

from contracts.types import ReviewRequest, ReviewResult


@runtime_checkable
class ReviewAgent(Protocol):
    """Contract for anything that can run a persona review.

    ``runtime_checkable`` so code can use ``isinstance(obj, ReviewAgent)``
    as a lightweight sanity check at module boundaries.
    """

    def run(self, request: ReviewRequest) -> ReviewResult:
        """Execute a review and return a structured result.

        Must not raise for recoverable errors — encode them in
        ``ReviewResult.raw["error"]`` instead.
        """
        ...


@runtime_checkable
class IntelligenceProvider(Protocol):
    """Contract for loading project intelligence."""

    def get(self, project_id: str) -> Dict[str, Any]:
        """Return the built intelligence dict, or ``{}`` if not yet built."""
        ...

    def build(
        self,
        project_id: str,
        version_label: Optional[str] = None,
        ai_backend: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build (or rebuild) intelligence and return the result dict."""
        ...


@runtime_checkable
class DeepDiveAgent(Protocol):
    """Contract for SME question generation."""

    def run(
        self,
        project_id: str,
        persona_name: str,
        custom_prompt: str = "",
        weaknesses: Optional[List[Dict[str, Any]]] = None,
        missing_categories: Optional[List[str]] = None,
        decision_points: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Generate and return SME question groups."""
        ...


@runtime_checkable
class ProposalAgent(Protocol):
    """Contract for proposal document generation."""

    def generate(
        self,
        project_id: str,
        proposal_ver_id: str,
        hierarchy_version_id: str,
        review_id: str,
        ai_backend: str = "files_only",
        force: bool = False,
    ) -> Dict[str, Any]:
        """Generate a proposal document and return the result dict."""
        ...


# ── Default (service-backed) implementations ─────────────────────────────────
# These thin adapters satisfy the Protocols using the existing services so
# callers that depend on the Protocol interface work immediately without
# any additional wiring.

class ServiceReviewAgent:
    """ReviewAgent backed by services.review.run_persona_review."""

    def run(self, request: ReviewRequest) -> ReviewResult:
        import services.review as svc
        raw = svc.run_persona_review(
            project_id=request.project_id,
            persona_name=request.roles,
            ai_backend=request.ai_backend,
            custom_prompt=request.custom_prompt,
            previous_review_id=request.previous_review_id,
            prompt_builder_state=request.prompt_builder_state,
        )
        return ReviewResult.from_service_dict(request.project_id, raw)


class ServiceIntelligenceProvider:
    """IntelligenceProvider backed by services.intelligence."""

    def get(self, project_id: str) -> Dict[str, Any]:
        import services.intelligence as svc
        return svc.get_project_intelligence(project_id)

    def build(
        self,
        project_id: str,
        version_label: Optional[str] = None,
        ai_backend: Optional[str] = None,
    ) -> Dict[str, Any]:
        import services.intelligence as svc
        return svc.build_project_intelligence(project_id, version_label, ai_backend)


class ServiceDeepDiveAgent:
    """DeepDiveAgent backed by services.deepdive.run_deep_dive_analysis."""

    def run(
        self,
        project_id: str,
        persona_name: str,
        custom_prompt: str = "",
        weaknesses: Optional[List[Dict[str, Any]]] = None,
        missing_categories: Optional[List[str]] = None,
        decision_points: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        import services.deepdive as svc
        return svc.run_deep_dive_analysis(
            project_id, persona_name, custom_prompt,
            weaknesses=weaknesses,
            missing_categories=missing_categories,
            decision_points=decision_points,
        )


class ServiceProposalAgent:
    """ProposalAgent backed by services.proposal.generate_proposal_doc."""

    def generate(
        self,
        project_id: str,
        proposal_ver_id: str,
        hierarchy_version_id: str,
        review_id: str,
        ai_backend: str = "files_only",
        force: bool = False,
    ) -> Dict[str, Any]:
        import services.proposal as svc
        return svc.generate_proposal_doc(
            project_id, proposal_ver_id, hierarchy_version_id,
            review_id, ai_backend, force,
        )
