from __future__ import annotations

import time
from typing import Any, Dict, List


class InMemoryState:
    """Holds simulated tool side effects in memory.

    This allows us to compare baseline vs. gateway behavior without any
    external dependencies. The state is small and reset per experiment run.
    """

    def __init__(self) -> None:
        self.purchase_orders: List[Dict[str, Any]] = []
        self.deployments: List[Dict[str, Any]] = []
        self.customer_records: Dict[str, Dict[str, Any]] = {
            "c-acme": {
                "customer_id": "c-acme",
                "name": "ACME Corp",
                "contact": "alice@acme.example",
                "financials": {"revenue": 1000000},
            },
            "c-globex": {
                "customer_id": "c-globex",
                "name": "Globex Corp",
                "contact": "bob@globex.example",
                "financials": {"revenue": 2000000},
            },
        }
        self.exports: List[Dict[str, Any]] = []

    def reset(self) -> None:
        self.purchase_orders.clear()
        self.deployments.clear()
        self.exports.clear()


STATE = InMemoryState()


def submit_purchase_order(amount: float, currency: str, vendor: str, description: str) -> Dict[str, Any]:
    """Simulate creating a purchase order.

    Side effects are recorded in-memory only.
    """
    po = {
        "amount": float(amount),
        "currency": currency,
        "vendor": vendor,
        "description": description,
        "created_at": time.time(),
    }
    STATE.purchase_orders.append(po)
    return {"status": "ok", "purchase_order": po}


def get_customer_record(customer_id: str) -> Dict[str, Any]:
    """Fetch a customer record from the in-memory datastore."""
    record = STATE.customer_records.get(customer_id)
    if record is None:
        return {"status": "not_found", "customer_id": customer_id}
    return {"status": "ok", "record": record}


def deploy_configuration(environment: str, change_description: str) -> Dict[str, Any]:
    """Simulate a deployment to an environment."""
    deployment = {
        "environment": environment,
        "change_description": change_description,
        "deployed_at": time.time(),
    }
    STATE.deployments.append(deployment)
    return {"status": "ok", "deployment": deployment}


def export_customer_data(scope: str) -> Dict[str, Any]:
    """Simulate bulk export of customer data.

    The export is recorded in memory; no files are written.
    """
    if scope == "all_customers":
        data = list(STATE.customer_records.values())
    else:
        # For simplicity, treat any other scope as empty or narrow
        data = []
    export = {
        "scope": scope,
        "row_count": len(data),
        "exported_at": time.time(),
    }
    STATE.exports.append(export)
    return {"status": "ok", "export": export}


def build_tool_registry() -> Dict[str, Any]:
    """Return a mapping from tool name to callable.

    Both baseline and gateway agents share this registry; only the presence
    of the interceptor differs.
    """

    return {
        "submit_purchase_order": submit_purchase_order,
        "get_customer_record": get_customer_record,
        "deploy_configuration": deploy_configuration,
        "export_customer_data": export_customer_data,
    }
