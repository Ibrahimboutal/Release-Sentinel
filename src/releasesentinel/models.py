from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


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


class RiskAssessment(BaseModel):
    change_id: str
    score: int = Field(ge=0, le=100)
    level: RiskLevel
    impacted_capabilities: list[str]
    drivers: list[str]
    confidence: float = Field(ge=0, le=1)


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


class FailureTriage(BaseModel):
    test_case_key: str
    test_case_name: str
    category: TriageCategory
    confidence: float = Field(ge=0, le=1)
    evidence: list[str]
    recommended_fix: str
    requires_human_review: bool


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
