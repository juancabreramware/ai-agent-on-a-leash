from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from .store import InMemoryStore, VersionedStore
from .invariants import InvariantsEngine
from .forensic_logging import ForensicLogger
from .workloads import WorkloadAgent, WorkloadProfile


@dataclass
class RecoveryRunInfo:
    steps_executed: int
    incident_detected: bool
    detection_step_id: Optional[int]
    rollback_checkpoint_id: Optional[str]
    recovery_outcome: str


class RecoveryManager:
    def __init__(self, store: VersionedStore, engine: InvariantsEngine) -> None:
        self.store = store
        self.engine = engine

    def on_violation(self, run_id: str, step_id: int) -> RecoveryRunInfo:
        # rollback to latest snapshot if available
        latest = self.store.latest_snapshot_id()
        if latest is not None:
            self.store.restore_snapshot(latest)
            outcome = "recovered_and_aborted"
        else:
            outcome = "failed_recovery"
        return RecoveryRunInfo(
            steps_executed=step_id + 1,
            incident_detected=True,
            detection_step_id=step_id,
            rollback_checkpoint_id=latest,
            recovery_outcome=outcome,
        )


class RecoveryOrchestrator:
    """Incident-ready orchestrator with snapshots, invariants, and rollback."""

    def __init__(self, seed: int, checkpoint_interval: int = 5) -> None:
        self.seed = seed
        self.checkpoint_interval = checkpoint_interval

    def _apply_action(self, store: VersionedStore, action: Dict[str, Any]) -> None:
        t = action["type"]
        if t == "transfer":
            store.transfer(action["src"], action["dst"], int(action["amount"]))
        elif t == "corruption":
            store.set_balance(action["target"], int(action["amount"]))
        elif t == "summary_corruption":
            state = store.get_state()
            total = int(state.get("summary_total", 0))
            factor = int(action.get("factor", 2))
            store.set_summary_total(total * factor)
        else:
            raise ValueError(f"Unknown action type: {t}")

    def run_workload(
        self,
        initial_state: Dict[str, Any],
        profile: WorkloadProfile,
    ) -> Tuple[Dict[str, Any], RecoveryRunInfo]:
        base_store = InMemoryStore(initial_state)
        vstore = VersionedStore(base_store)
        engine = InvariantsEngine()
        agent = WorkloadAgent(seed=self.seed)
        actions = agent.generate_actions(profile)

        run_id = f"{profile.name}_seed{self.seed}"
        logger = ForensicLogger(run_id=run_id)
        manager = RecoveryManager(vstore, engine)

        incident_info: Optional[RecoveryRunInfo] = None

        # initial checkpoint
        vstore.create_snapshot(reason="start", run_id=run_id, step_id=-1)

        for step_id, action in enumerate(actions):
            # periodic checkpoint before action
            if step_id % self.checkpoint_interval == 0:
                vstore.create_snapshot(reason="periodic", run_id=run_id, step_id=step_id)

            before_state = vstore.get_state().copy()
            self._apply_action(vstore, action)
            after_state = vstore.get_state().copy()

            inv_result = engine.check(after_state)

            logger.log_step(
                {
                    "step_id": step_id,
                    "action": action,
                    "invariants_evaluated": True,
                    "invariants_status": "pass" if inv_result.ok else "fail",
                    "invariants_errors": inv_result.errors,
                }
            )

            if not inv_result.ok:
                incident_info = manager.on_violation(run_id, step_id)
                break

        logger.close()

        if incident_info is None:
            incident_info = RecoveryRunInfo(
                steps_executed=len(actions),
                incident_detected=False,
                detection_step_id=None,
                rollback_checkpoint_id=None,
                recovery_outcome="no_incident",
            )

        return vstore.get_state(), incident_info
