import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "deadline_guard_v1"

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
        self._lock_on_demand = False
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If already completed (safety guard)
        work_done = sum(self.task_done_time) if self.task_done_time else 0.0
        remaining_work = max(self.task_duration - work_done, 0.0)

        if remaining_work <= 0:
            return ClusterType.NONE

        # If previously locked into ON_DEMAND, keep using it
        if self._lock_on_demand:
            return ClusterType.ON_DEMAND

        # Core safety computations
        E = self.env.elapsed_seconds
        H = float(self.restart_overhead)
        gap = float(self.env.gap_seconds)
        D = float(self.deadline)

        # Safe to continue with one more SPOT step if even after that,
        # immediately switching to ON_DEMAND (with one restart) meets the deadline.
        safe_to_use_spot = (E + H + remaining_work) <= (D + 1e-9)

        # If SPOT available and safe, use SPOT
        if has_spot and safe_to_use_spot:
            return ClusterType.SPOT

        # If SPOT not available, consider idling if safe to do so for one step
        if not has_spot:
            safe_to_idle = (E + gap + H + remaining_work) <= (D + 1e-9)
            if safe_to_idle:
                return ClusterType.NONE
            # Otherwise, must switch to ON_DEMAND to avoid missing deadline
            self._lock_on_demand = True
            return ClusterType.ON_DEMAND

        # SPOT available but no longer safe to risk it -> switch to ON_DEMAND
        self._lock_on_demand = True
        return ClusterType.ON_DEMAND
