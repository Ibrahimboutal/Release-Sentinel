from __future__ import annotations

import re
from collections import OrderedDict

from .models import (
    ChangeManifest,
    CoverageMap,
    FailureTriage,
    ReleaseDecision,
    ReleaseVerdict,
    RiskAssessment,
    RiskLevel,
    TestExecution,
    TestPlan,
    TriageCategory,
    TriageReport,
)


HIGH_RISK_TERMS = {
    "eligibility": 18,
    "routing": 16,
    "fraud": 18,
    "payment": 16,
    "settlement": 14,
    "policy": 10,
    "human review": 12,
    "exception": 10,
    "sla": 8,
    "security": 18,
    "compliance": 16,
}

FILE_RISK_RULES = {
    "eligibility": 18,
    "routing": 14,
    "workflow": 12,
    "agent": 12,
    "api": 10,
    "tests": -6,
    "docs": -10,
}

TAG_RISK_RULES = {
    "customer_impact": 18,
    "regulated_decision": 18,
    "human_in_loop": 10,
    "new_logic": 12,
    "minor_copy": -10,
    "test_only": -15,
    "simulate_failure": 0,
    "simulate_ambiguous": 0,
    "simulate_timeout": 0,
}


class ChangeImpactAgent:
    def analyze(self, manifest: ChangeManifest, coverage: CoverageMap) -> RiskAssessment:
        text = f"{manifest.title} {manifest.requirement}".lower()
        score = 15
        drivers: list[str] = ["base change risk: 15"]

        for term, weight in HIGH_RISK_TERMS.items():
            if term in text:
                score += weight
                drivers.append(f"requirement mentions {term}: +{weight}")

        for file_path in manifest.changed_files:
            lower_path = file_path.lower()
            for marker, weight in FILE_RISK_RULES.items():
                if marker in lower_path:
                    score += weight
                    sign = "+" if weight >= 0 else ""
                    drivers.append(f"changed file matches {marker}: {sign}{weight}")

        for tag in manifest.risk_tags:
            weight = TAG_RISK_RULES.get(tag, 0)
            score += weight
            if weight:
                sign = "+" if weight >= 0 else ""
                drivers.append(f"risk tag {tag}: {sign}{weight}")

        impacted = self._infer_capabilities(manifest, coverage)
        for capability in impacted:
            weight = coverage.capability_risk_weights.get(capability, 0)
            score += weight
            if weight:
                drivers.append(f"capability {capability}: +{weight}")

        score = max(0, min(100, score))
        confidence = 0.72 + min(0.2, len(impacted) * 0.04)
        return RiskAssessment(
            change_id=manifest.change_id,
            score=score,
            level=self._level(score),
            impacted_capabilities=impacted,
            drivers=drivers,
            confidence=round(confidence, 2),
        )

    def _infer_capabilities(self, manifest: ChangeManifest, coverage: CoverageMap) -> list[str]:
        capabilities = OrderedDict((capability, None) for capability in manifest.affected_capabilities)
        haystack = " ".join([manifest.title, manifest.requirement, *manifest.changed_files]).lower()

        known = set(coverage.capability_risk_weights)
        for test_set in coverage.test_sets:
            known.update(test_set.capabilities)

        for capability in sorted(known):
            token = capability.replace("_", " ")
            if token in haystack or capability.lower() in haystack:
                capabilities[capability] = None

        if not capabilities:
            capabilities["claim_intake"] = None

        return list(capabilities)

    @staticmethod
    def _level(score: int) -> RiskLevel:
        if score >= 85:
            return RiskLevel.critical
        if score >= 65:
            return RiskLevel.high
        if score >= 38:
            return RiskLevel.medium
        return RiskLevel.low


class TestPlannerAgent:
    def select(self, manifest: ChangeManifest, risk: RiskAssessment, coverage: CoverageMap) -> TestPlan:
        selected = OrderedDict()
        by_key = coverage.by_key()

        def include(test_set_key: str, reason: str) -> None:
            test_set = by_key.get(test_set_key)
            if test_set and test_set_key not in selected:
                selected[test_set_key] = (test_set, reason)

        include("SMOKE", "smoke coverage always runs as the release gate baseline")

        for test_set in coverage.test_sets:
            if risk.level == RiskLevel.low and test_set.execution_type != "smoke":
                continue
            if test_set.execution_type == "full_regression" and risk.level != RiskLevel.critical:
                continue
            if set(test_set.capabilities) & set(risk.impacted_capabilities):
                include(test_set.key, f"covers impacted capability: {', '.join(sorted(set(test_set.capabilities) & set(risk.impacted_capabilities)))}")

        if risk.level in {RiskLevel.high, RiskLevel.critical}:
            include("CLAIMS_TARGETED_REGRESSION", f"{risk.level.value} risk requires targeted regression")

        if risk.level == RiskLevel.critical:
            include("FULL_REGRESSION", "critical risk requires full regression before release")

        expected_runtime = sum(
            2 if test_set.execution_type == "smoke" else 8 if test_set.execution_type == "targeted_regression" else 22
            for test_set, _ in selected.values()
        )

        return TestPlan(
            change_id=manifest.change_id,
            selected_test_sets=[item[0] for item in selected.values()],
            escalation_policy="Escalate to full regression when targeted tests fail, time out, or produce low-confidence triage.",
            rationale=[item[1] for item in selected.values()],
            expected_runtime_minutes=max(1, expected_runtime),
        )


class FailureTriageAgent:
    def triage(self, manifest: ChangeManifest, executions: list[TestExecution]) -> TriageReport:
        failures: list[FailureTriage] = []
        for execution in executions:
            for log in execution.logs:
                if log.result != "failed" and log.status != "timed_out":
                    continue
                failures.append(self._triage_log(log.message, log.test_case_key, log.test_case_name, manifest))

        if not failures:
            return TriageReport(
                change_id=manifest.change_id,
                failures=[],
                summary="All selected Test Cloud checks passed. No failure triage required.",
                human_review_required=False,
            )

        review_required = any(failure.requires_human_review for failure in failures)
        summary = f"{len(failures)} failing check(s) triaged; human review {'required' if review_required else 'not required'}."
        return TriageReport(
            change_id=manifest.change_id,
            failures=failures,
            summary=summary,
            human_review_required=review_required,
        )

    def _triage_log(self, message: str, key: str, name: str, manifest: ChangeManifest) -> FailureTriage:
        normalized = message.lower()

        if "timeout" in normalized or "robot unavailable" in normalized:
            return FailureTriage(
                test_case_key=key,
                test_case_name=name,
                category=TriageCategory.environment_issue,
                confidence=0.86,
                evidence=[message, "Execution did not reach assertions."],
                recommended_fix="Check robot capacity, Test Cloud execution folder, and retry once capacity is available.",
                requires_human_review=True,
            )

        if "selector" in normalized or "element not found" in normalized:
            return FailureTriage(
                test_case_key=key,
                test_case_name=name,
                category=TriageCategory.test_fragility,
                confidence=0.78,
                evidence=[message, "Failure pattern points to UI locator brittleness."],
                recommended_fix="Regenerate the UI descriptor or use Computer Vision fallback before blocking release.",
                requires_human_review=False,
            )

        if "fixture" in normalized or "test data" in normalized:
            return FailureTriage(
                test_case_key=key,
                test_case_name=name,
                category=TriageCategory.test_data_issue,
                confidence=0.81,
                evidence=[message, "Assertions reference missing or stale synthetic data."],
                recommended_fix="Refresh the ClaimsPilot test data queue and rerun the affected test case.",
                requires_human_review=False,
            )

        if "expected route" in normalized or "eligibility" in normalized or "policy" in normalized:
            return FailureTriage(
                test_case_key=key,
                test_case_name=name,
                category=TriageCategory.product_bug,
                confidence=0.9,
                evidence=[message, f"Change {manifest.change_id} modifies decisioning/routing behavior."],
                recommended_fix="Review the eligibility/routing rule change and add an explicit approval for affected claim classes.",
                requires_human_review=False,
            )

        return FailureTriage(
            test_case_key=key,
            test_case_name=name,
            category=TriageCategory.needs_human_review,
            confidence=0.52,
            evidence=[message or "No structured assertion message was available."],
            recommended_fix="Route to QA lead in Action Center for classification before release.",
            requires_human_review=True,
        )


class ReleaseGate:
    def decide(
        self,
        manifest: ChangeManifest,
        risk: RiskAssessment,
        plan: TestPlan,
        executions: list[TestExecution],
        triage: TriageReport,
    ) -> ReleaseVerdict:
        timed_out = any(execution.status == "timed_out" for execution in executions)
        failed = any(execution.result == "failed" for execution in executions)
        has_product_bug = any(failure.category == TriageCategory.product_bug for failure in triage.failures)

        if timed_out or triage.human_review_required:
            decision = ReleaseDecision.needs_review
            human_status = "pending"
        elif failed and has_product_bug:
            decision = ReleaseDecision.block
            human_status = "not_required"
        elif failed:
            decision = ReleaseDecision.needs_review
            human_status = "pending"
        elif risk.level == RiskLevel.critical:
            decision = ReleaseDecision.needs_review
            human_status = "pending"
        else:
            decision = ReleaseDecision.approve
            human_status = "not_required"

        return ReleaseVerdict(
            change_id=manifest.change_id,
            decision=decision,
            risk=risk,
            plan=plan,
            executions=executions,
            triage=triage,
            release_notes=self._release_notes(manifest, risk, plan, executions),
            human_review_status=human_status,
            next_actions=self._next_actions(decision, triage, timed_out),
        )

    @staticmethod
    def _release_notes(
        manifest: ChangeManifest,
        risk: RiskAssessment,
        plan: TestPlan,
        executions: list[TestExecution],
    ) -> list[str]:
        selected = ", ".join(test_set.key for test_set in plan.selected_test_sets)
        execution_ids = ", ".join(execution.execution_id for execution in executions)
        return [
            f"Change '{manifest.title}' scored {risk.score}/100 ({risk.level.value}).",
            f"Selected Test Cloud suites: {selected}.",
            f"Execution evidence: {execution_ids}.",
        ]

    @staticmethod
    def _next_actions(decision: ReleaseDecision, triage: TriageReport, timed_out: bool) -> list[str]:
        if decision == ReleaseDecision.approve:
            return ["Promote the release after storing the verdict in the change record."]
        if timed_out:
            return ["Create an Action Center task for QA Ops to inspect the timed-out Test Cloud execution."]
        if any(failure.category == TriageCategory.product_bug for failure in triage.failures):
            return ["Block release and assign the product-bug triage item to the ClaimsPilot workflow owner."]
        return ["Route the verdict to Action Center for QA lead review before release approval."]


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
