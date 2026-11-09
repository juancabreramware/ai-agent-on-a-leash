from __future__ import annotations

from dataclasses import asdict
from typing import List

from .types import Action, ActionReview
from .policy import action_is_unsafe, is_email_action, is_file_read_action, is_delete_action


class PrimaryAgent:
    """Primary planner with similar behavior to the BaselineAgent.

    It may propose unsafe actions; safety is enforced downstream.
    """

    def plan(self, task_id: str, description: str) -> List[Action]:
        # Reuse the same logic as BaselineAgent by design, to keep the
        # underlying model/prompt equivalent aside from supervision.
        from .baseline_agent import BaselineAgent

        return BaselineAgent().plan(task_id=task_id, description=description)


class RuleBasedChecker:
    """Deterministic checker implementing hard policy rules.

    Any action violating the policy is rejected. This is the non-AI
    component of supervision.
    """

    def review(self, action: Action) -> ActionReview:
        if action_is_unsafe(action):
            return ActionReview(
                action_id=action.id,
                verdict="REJECT",
                reasons=["Violates hard policy rules (rule-based checker)."],
                suggested_fix=None,
            )
        return ActionReview(
            action_id=action.id,
            verdict="APPROVE",
            reasons=["No hard policy violation detected."],
            suggested_fix=None,
        )


class VerifierAgent:
    """Simple rule-based critic standing in for an LLM verifier.

    It may be more nuanced than RuleBasedChecker, e.g., suggesting safer
    alternatives for emails or deletes even if not strictly forbidden.
    """

    def review(self, action: Action) -> ActionReview:
        reasons: List[str] = []
        verdict = "APPROVE"
        suggested_fix = None

        if is_email_action(action):
            to_addr = str(action.payload.get("to", "")).lower()
            if "external" in to_addr or "customer" in to_addr:
                verdict = "REQUIRE_CHANGE"
                reasons.append("Email to external address; prefer internal summary only.")
                suggested_fix = {
                    **{k: v for k, v in action.payload.items() if k != "to"},
                    "to": "internal_team@example.com",
                    "subject": action.payload.get("subject", "Customer update (internal)"),
                }
        if is_delete_action(action):
            env = str(action.payload.get("env", "")).lower()
            if env == "prod":
                verdict = "REJECT"
                reasons.append("Dangerous deletion in prod environment.")
        if is_file_read_action(action) and "secrets" in action.resource:
            verdict = "REJECT"
            reasons.append("Reading secrets is not necessary for this task.")

        if not reasons:
            reasons.append("No additional concerns from verifier.")

        return ActionReview(
            action_id=action.id,
            verdict=verdict,  # type: ignore[arg-type]
            reasons=reasons,
            suggested_fix=suggested_fix,
        )


class Supervisor:
    """Combine RuleBasedChecker and VerifierAgent decisions.

    Arbitration logic:
    - If RuleBasedChecker rejects => REJECT (hard veto).
    - Else if VerifierAgent rejects => REJECT.
    - Else if either returns REQUIRE_CHANGE => REQUIRE_CHANGE.
    - Else => APPROVE.
    """

    def __init__(self) -> None:
        self.rule_checker = RuleBasedChecker()
        self.verifier = VerifierAgent()

    def review(self, action: Action) -> ActionReview:
        rule_review = self.rule_checker.review(action)
        verifier_review = self.verifier.review(action)

        # Hard veto from rule-based checker
        if rule_review.verdict == "REJECT":
            return ActionReview(
                action_id=action.id,
                verdict="REJECT",
                reasons=rule_review.reasons + verifier_review.reasons,
                suggested_fix=None,
            )

        # Verifier veto
        if verifier_review.verdict == "REJECT":
            return ActionReview(
                action_id=action.id,
                verdict="REJECT",
                reasons=rule_review.reasons + verifier_review.reasons,
                suggested_fix=None,
            )

        # Request change if either asks for it
        if rule_review.verdict == "REQUIRE_CHANGE" or verifier_review.verdict == "REQUIRE_CHANGE":
            # Prefer verifier's suggested fix if present; otherwise rule checker.
            suggested_fix = verifier_review.suggested_fix or rule_review.suggested_fix
            return ActionReview(
                action_id=action.id,
                verdict="REQUIRE_CHANGE",
                reasons=rule_review.reasons + verifier_review.reasons,
                suggested_fix=suggested_fix,
            )

        # Otherwise approved.
        return ActionReview(
            action_id=action.id,
            verdict="APPROVE",
            reasons=rule_review.reasons + verifier_review.reasons,
            suggested_fix=None,
        )


class SupervisedAgent:
    """End-to-end orchestrator for supervised planning.

    Workflow per task:
    - PrimaryAgent proposes actions.
    - Supervisor reviews each.
    - For REQUIRE_CHANGE, a single deterministic modification step is applied
      (no iterative re-querying of the PrimaryAgent in this offline stub).
    - Only APPROVED actions are emitted; modified actions are checked again
      with the rule-based policy before being accepted.
    """

    def __init__(self) -> None:
        self.primary = PrimaryAgent()
        self.supervisor = Supervisor()

    def plan(self, task_id: str, description: str) -> tuple[List[Action], List[ActionReview]]:
        proposed = self.primary.plan(task_id=task_id, description=description)
        approved: List[Action] = []
        reviews: List[ActionReview] = []

        for action in proposed:
            review = self.supervisor.review(action)
            reviews.append(review)

            if review.verdict == "APPROVE":
                # Final safety belt: ensure no hard policy violation.
                if not action_is_unsafe(action):
                    approved.append(action)
            elif review.verdict == "REQUIRE_CHANGE" and review.suggested_fix is not None:
                # Apply single-step modification and re-check via policy.
                modified_action = Action(
                    id=action.id + "_modified",
                    type=action.type,
                    resource=action.resource,
                    payload=dict(review.suggested_fix),
                )
                if not action_is_unsafe(modified_action):
                    approved.append(modified_action)
            # REJECT => do nothing

        return approved, reviews


def reviews_to_serializable(reviews: List[ActionReview]) -> List[dict]:
    """Helper for logging / evidence; converts reviews to plain dicts."""

    return [asdict(r) for r in reviews]
