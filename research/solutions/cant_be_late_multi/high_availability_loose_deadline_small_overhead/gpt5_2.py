import json
from argparse import Namespace
from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "jit_guard_od_lock_v1"

    def solve(self, spec_path: str) -> "Solution":
        with open(spec_path) as f:
            config = json.load(f)

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)

        # Internal state
        self._od_locked = False
        self._last_reset_marker = -1.0
        return self

    def _maybe_reset_internal_state(self):
        # Reset lock at the start of each new scenario/run
        cur = getattr(self.env, "elapsed_seconds", 0.0)
        if cur < self._last_reset_marker or cur == 0.0:
            self._od_locked = False
        self._last_reset_marker = cur

    def _get_remaining_compute(self) -> float:
        done = sum(self.task_done_time) if hasattr(self, "task_done_time") else 0.0
        remaining = self.task_duration - done
        if remaining < 0.0:
            remaining = 0.0
        return remaining

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._maybe_reset_internal_state()

        # Basic stats
        t_elapsed = self.env.elapsed_seconds
        slack = self.deadline - t_elapsed
        gap = self.env.gap_seconds
        R = self._get_remaining_compute()

        if R <= 0.0:
            return ClusterType.NONE

        # If we are already locked to OD, keep using OD to ensure deadline feasibility.
        if self._od_locked:
            return ClusterType.ON_DEMAND

        # Compute time needed if we start OD now
        if last_cluster_type == ClusterType.ON_DEMAND:
            od_overhead_now = max(0.0, self.remaining_restart_overhead)
        else:
            od_overhead_now = self.restart_overhead

        # If we cannot guarantee completion unless we start OD now, lock and go OD.
        if slack <= od_overhead_now + R:
            self._od_locked = True
            return ClusterType.ON_DEMAND

        # Prefer SPOT when available
        if has_spot:
            return ClusterType.SPOT

        # Spot not available: decide wait vs OD
        # If we can afford to wait one full step and still complete by switching to OD next step, then wait.
        extra_slack_if_commit_next_step = slack - gap - (self.restart_overhead + R)
        if extra_slack_if_commit_next_step > 0.0:
            return ClusterType.NONE

        # Otherwise, we must commit to OD now
        self._od_locked = True
        return ClusterType.ON_DEMAND