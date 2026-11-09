from dataclasses import dataclass
from typing import Dict, Any, List


@dataclass
class WorkloadVariant:
    workload_id: str
    variant_id: str
    description: str
    payload: Dict[str, Any]


def get_all_variants() -> List[WorkloadVariant]:
    """Return all workload variants with deterministic payloads."""

    variants: List[WorkloadVariant] = []

    # wf-1 variants: incident reports
    variants.append(
        WorkloadVariant(
            workload_id="wf-1",
            variant_id="wf-1a-clear-incident",
            description="Well-structured incident report with clear severity.",
            payload={
                "document": """TITLE: SEV-1 Outage\nUsers cannot access the service.\n""",
            },
        )
    )

    variants.append(
        WorkloadVariant(
            workload_id="wf-1",
            variant_id="wf-1b-ambiguous-incident",
            description="Mixed issues requiring careful extraction.",
            payload={
                "document": """Report: Intermittent failures and slow responses.\nSome users see errors, others only latency.\n""",
            },
        )
    )

    # wf-2 variants: data cleaning plans
    variants.append(
        WorkloadVariant(
            workload_id="wf-2",
            variant_id="wf-2a-simple-missing-values",
            description="Simple null-value problems.",
            payload={
                "schema": {"user_id": "int", "age": "int"},
                "issue": "Some rows have null age values.",
            },
        )
    )

    variants.append(
        WorkloadVariant(
            workload_id="wf-2",
            variant_id="wf-2b-mixed-quality-issues",
            description="Mixed type inconsistencies and outliers.",
            payload={
                "schema": {"price": "float", "category": "str"},
                "issue": "Price has strings and extreme outliers.",
            },
        )
    )

    return variants
