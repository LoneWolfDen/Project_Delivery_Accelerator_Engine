"""Tests for core data models."""

from models.project import Project, ProjectContext, ReviewOutput


class TestProject:
    """Validate Project model."""

    def test_create_default_project(self):
        p = Project()
        assert p.id == ""
        assert p.phase == "discovery"
        assert p.ai_backend == "ollama"
        assert p.files == []
        assert p.reviews == []
        assert p.context is None

    def test_create_project_with_values(self):
        p = Project(
            id="proj-001",
            name="Test Project",
            description="A test",
            phase="proposal",
            ai_backend="bedrock",
        )
        assert p.id == "proj-001"
        assert p.name == "Test Project"
        assert p.phase == "proposal"
        assert p.ai_backend == "bedrock"

    def test_project_valid_phases(self):
        valid_phases = ["discovery", "proposal", "planning", "execution", "review"]
        for phase in valid_phases:
            p = Project(phase=phase)
            assert p.phase == phase


class TestProjectContext:
    """Validate ProjectContext model."""

    def test_create_empty_context(self):
        ctx = ProjectContext()
        assert ctx.scope == ""
        assert ctx.risks == []
        assert ctx.assumptions == []
        assert ctx.dependencies == []
        assert ctx.resources == []
        assert ctx.constraints == []

    def test_create_context_with_data(self):
        ctx = ProjectContext(
            scope="Migrate 20 apps to AWS",
            risks=["Skill gap", "Timeline risk"],
            assumptions=["Budget approved", "Team available"],
            dependencies=["Network setup", "Security review"],
        )
        assert len(ctx.risks) == 2
        assert "Skill gap" in ctx.risks
        assert ctx.scope == "Migrate 20 apps to AWS"


class TestReviewOutput:
    """Validate ReviewOutput model."""

    def test_create_review(self):
        review = ReviewOutput(
            persona="solution_architect",
            risks=["No DR strategy"],
            gaps=["Missing auth design"],
            recommendations=["Add failover plan"],
            questions=["What is the RPO target?"],
        )
        assert review.persona == "solution_architect"
        assert len(review.risks) == 1
        assert review.timestamp  # Should auto-set
