from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

from context_tokens import ContextToken


# Sensitivity levels for memory items.
SENSITIVITY_NORMAL = "normal"
SENSITIVITY_PII = "pii"
SENSITIVITY_SECRET = "secret"


@dataclass
class PolicyDecision:
    allowed: bool
    reason: str


class AccessPolicy:
    """Static access-control and redaction policy.

    The policy is intentionally simple and deterministic:
    - Isolation is by "scope" strings such as
      "tenant:acme_corp:task1" or "tenant:acme_corp:shared".
    - ContextToken.allowed_scopes must contain the item's scope for
    access to be granted.
    - Redaction rules depend on the caller's role and item sensitivity.
    """

    # Roles that may see unredacted PII and secrets.
    PRIVILEGED_ROLES = {"auditor"}

    @staticmethod
    def can_access_scope(ctx: ContextToken, item_scope: str) -> PolicyDecision:
        if item_scope in ctx.allowed_scopes:
            return PolicyDecision(True, "allowed: scope_match")
        return PolicyDecision(False, "denied: scope_mismatch")

    @staticmethod
    def needs_redaction(ctx: ContextToken, sensitivity: str) -> bool:
        """Return True if the caller should see redacted view.

        - Normal sensitivity: never redacted.
        - PII: redacted unless caller is privileged.
        - Secret: redacted unless caller is privileged.
        """

        if sensitivity == SENSITIVITY_NORMAL:
            return False
        if ctx.role in AccessPolicy.PRIVILEGED_ROLES:
            return False
        return True

    @staticmethod
    def redact_fields(data: Dict[str, str], fields: Iterable[str]) -> Dict[str, str]:
        """Return a shallow copy with certain fields masked.

        This is deterministic and intentionally simple to keep tests
        predictable.
        """

        masked = dict(data)
        for field in fields:
            if field in masked and isinstance(masked[field], str):
                original = masked[field]
                if not original:
                    continue
                # Keep first 2 and last 2 characters when possible.
                if len(original) > 4:
                    masked[field] = original[:2] + "***" + original[-2:]
                else:
                    masked[field] = "*" * len(original)
        return masked


def apply_redaction(
    ctx: ContextToken,
    sensitivity: str,
    record: Dict[str, str],
    pii_fields: Iterable[str],
    secret_fields: Iterable[str],
) -> Tuple[Dict[str, str], bool]:
    """Apply redaction rules based on context and sensitivity.

    Returns `(possibly_redacted_record, redacted_applied: bool)`.
    """

    if not AccessPolicy.needs_redaction(ctx, sensitivity):
        return dict(record), False

    fields: List[str] = []
    if sensitivity == SENSITIVITY_PII:
        fields.extend(pii_fields)
    elif sensitivity == SENSITIVITY_SECRET:
        fields.extend(secret_fields)
    else:
        return dict(record), False

    redacted = AccessPolicy.redact_fields(record, fields)
    changed = any(record.get(f) != redacted.get(f) for f in fields)
    return redacted, changed
