from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class RiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class ReleaseDecision(str, Enum):
    approve = "approve"
    needs_review = "needs_review"
    block = "block"


class TriageCategory(str, Enum):
    product_bug = "product_bug"
    test_fragility = "test_fragility"
    test_data_issue = "test_data_issue"
    environment_issue = "environment_issue"
    needs_human_review = "needs_human_review"


class ChangeManifest(BaseModel):
    change_id: str = Field(default_factory=lambda: f"chg-{uuid4().hex[:8]}")
    title: str
    requirement: str
    changed_files: list[str] = Field(default_factory=list)
    affected_capabilities: list[str] = Field(default_factory=list)
    risk_tags: list[str] = Field(default_factory=list)
    author: str = "demo.builder@example.com"
    pull_request_url: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("title", "requirement")
    @classmethod
    def validate_non_empty_strings(cls, v: str) -> str:
        """Ensure title and requirement are non-empty."""
        if not v or not v.strip():
            raise ValueError("title and requirement cannot be empty")
        return v.strip()

    @field_validator("author")
    @classmethod
    def validate_author_format(cls, v: str) -> str:
        """Basic validation for author email format."""
        if not v or not v.strip():
            raise ValueError("author cannot be empty")
        return v.strip()


class RiskAssessment(BaseModel):
    change_id: str
    score: int = Field(ge=0, le=100)
    level: RiskLevel
    impacted_capabilities: list[str]
    drivers: list[str]
    confidence: float = Field(ge=0, le=1)

    @field_validator("score")
    @classmethod
    def validate_score_range(cls, v: int) -> int:
        """Ensure score is always within valid range (0-100)."""
        if not (0 <= v <= 100):
            raise ValueError(f"score must be between 0 and 100, got {v}")
        return v

    @field_validator("confidence")
    @classmethod
    def validate_confidence_range(cls, v: float) -> float:
        """Ensure confidence is always within valid range (0.0-1.0)."""
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"confidence must be between 0.0 and 1.0, got {v}")
        return v

    @field_validator("level", mode="before")
    @classmethod
    def validate_level_consistency(cls, v: Any, info) -> RiskLevel:
        """Validate that risk level is consistent with score."""
        # Only perform this check if score is already available
        if hasattr(info, "data") and "score" in info.data:
            score = info.data["score"]
            if isinstance(v, str):
                v = RiskLevel(v)
            # Verify level is reasonable for the score
            if score >= 85 and v != RiskLevel.critical:
                raise ValueError(f"score {score} should have level critical, got {v}")
            if 65 <= score < 85 and v != RiskLevel.high:
                # Warning only, not an error
                pass
        return v

    @field_validator("drivers")
    @classmethod
    def validate_drivers(cls, v: list[str]) -> list[str]:
        """Ensure drivers list is non-empty and contains strings."""
        if not v:
            raise ValueError("drivers list cannot be empty")
        return [str(d).strip() for d in v if d.strip()]


class TestCaseRef(BaseModel):
    key: str
    name: str
    capability: str
    automation: str
    priority: Literal["P0", "P1", "P2"] = "P1"


class TestSetRef(BaseModel):
    key: str
    name: str
    execution_type: Literal["smoke", "targeted_regression", "full_regression"]
    capabilities: list[str]
    test_cases: list[TestCaseRef]


class CoverageMap(BaseModel):
    project_key: str
    default_folder_key: str | None = None
    test_sets: list[TestSetRef]
    capability_risk_weights: dict[str, int] = Field(default_factory=dict)

    def by_key(self) -> dict[str, TestSetRef]:
        return {test_set.key: test_set for test_set in self.test_sets}


class TestPlan(BaseModel):
    change_id: str
    selected_test_sets: list[TestSetRef]
    escalation_policy: str
    rationale: list[str]
    expected_runtime_minutes: int


class TestCaseLog(BaseModel):
    id: str = Field(default_factory=lambda: f"log-{uuid4().hex[:8]}")
    test_case_key: str
    test_case_name: str
    status: Literal["queued", "running", "finished", "timed_out", "skipped"]
    result: Literal["passed", "failed", "cancelled", "inconclusive", "skipped"]
    duration_seconds: int = 0
    message: str = ""
    assertions: list[str] = Field(default_factory=list)
    attachments: list[str] = Field(default_factory=list)

    @field_validator("duration_seconds")
    @classmethod
    def validate_duration(cls, v: int) -> int:
        """Ensure duration is non-negative."""
        if v < 0:
            raise ValueError(f"duration_seconds must be non-negative, got {v}")
        return v

    @field_validator("test_case_key", "test_case_name")
    @classmethod
    def validate_non_empty_keys(cls, v: str) -> str:
        """Ensure test case keys and names are non-empty."""
        if not v or not v.strip():
            raise ValueError("test_case_key and test_case_name cannot be empty")
        return v.strip()


class TestExecution(BaseModel):
    execution_id: str = Field(default_factory=lambda: f"exec-{uuid4().hex[:8]}")
    test_set_key: str
    test_set_name: str
    source: Literal["simulated", "uipath_test_manager"]
    status: Literal["queued", "running", "finished", "timed_out", "cancelled"]
    result: Literal["passed", "failed", "cancelled", "inconclusive"]
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None
    logs: list[TestCaseLog] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)

    @field_validator("test_set_key", "test_set_name")
    @classmethod
    def validate_non_empty_keys(cls, v: str) -> str:
        """Ensure test set keys and names are non-empty."""
        if not v or not v.strip():
            raise ValueError("test_set_key and test_set_name cannot be empty")
        return v.strip()


class FailureTriage(BaseModel):
    test_case_key: str
    test_case_name: str
    category: TriageCategory
    confidence: float = Field(ge=0, le=1)
    evidence: list[str]
    recommended_fix: str
    requires_human_review: bool

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        """Ensure confidence is between 0 and 1."""
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"confidence must be between 0.0 and 1.0, got {v}")
        return v

    @field_validator("test_case_key", "test_case_name")
    @classmethod
    def validate_non_empty_strings(cls, v: str) -> str:
        """Ensure test case key and name are non-empty."""
        if not v or not v.strip():
            raise ValueError("test_case_key and test_case_name cannot be empty")
        return v.strip()

    @field_validator("evidence")
    @classmethod
    def validate_evidence(cls, v: list[str]) -> list[str]:
        """Ensure evidence is non-empty."""
        if not v:
            raise ValueError("evidence list cannot be empty")
        return [str(e).strip() for e in v if e.strip()]

    @field_validator("recommended_fix")
    @classmethod
    def validate_recommended_fix(cls, v: str) -> str:
        """Ensure recommended_fix is non-empty."""
        if not v or not v.strip():
            raise ValueError("recommended_fix cannot be empty")
        return v.strip()


class TriageReport(BaseModel):
    change_id: str
    failures: list[FailureTriage]
    summary: str
    human_review_required: bool


class ReleaseVerdict(BaseModel):
    change_id: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    decision: ReleaseDecision
    risk: RiskAssessment
    plan: TestPlan
    executions: list[TestExecution]
    triage: TriageReport
    release_notes: list[str]
    human_review_status: Literal["not_required", "pending", "completed"] = "not_required"
    action_center_task_id: str | None = None
    next_actions: list[str]


class AnalyzeRequest(BaseModel):
    manifest: ChangeManifest


class SelectTestsRequest(BaseModel):
    manifest: ChangeManifest
    risk: RiskAssessment | None = None


class TriageRequest(BaseModel):
    manifest: ChangeManifest
    executions: list[TestExecution]
    flakiness_map: dict[str, float] = Field(default_factory=dict)


class VerdictRequest(BaseModel):
    manifest: ChangeManifest
    scenario: Literal["auto", "happy", "failing", "ambiguous", "timeout"] = "auto"
    persist: bool = True


class DemoRunRequest(BaseModel):
    scenario: Literal["happy", "failing", "ambiguous", "timeout"]
    manifest_path: str | None = None
    sync_coverage: bool = False
    runner: Literal["auto", "simulated", "uipath"] = "auto"
