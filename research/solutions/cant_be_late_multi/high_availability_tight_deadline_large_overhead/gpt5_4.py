import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_spot_first"

    def __init__(self, args=None):
        super().__init__(args)
        self._lock_to_od = False

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
        self._lock_to_od = False
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If already finished, no need to run more.
        work_done = sum(self.task_done_time) if self.task_done_time else 0.0
        remaining_work = max(0.0, self.task_duration - work_done)
        if remaining_work <= 0.0:
            return ClusterType.NONE

        # Compute time left to deadline.
        time_left = max(0.0, self.deadline - self.env.elapsed_seconds)

        # Decide if we must use On-Demand to finish in time.
        # Extra overhead to finish on OD from now:
        # - If already on OD, we only need to account for the remaining pending overhead.
        # - Otherwise, switching to OD incurs the restart overhead.
        if last_cluster_type == ClusterType.ON_DEMAND:
            od_overhead_needed = self.remaining_restart_overhead
        else:
            od_overhead_needed = self.restart_overhead

        od_time_needed = remaining_work + od_overhead_needed

        # If we already committed to On-Demand, stay there to avoid additional overheads and ensure completion.
        if self._lock_to_od:
            return ClusterType.ON_DEMAND

        # Safety check: if time left is not enough to wait any longer, switch to OD now.
        if time_left <= od_time_needed:
            self._lock_to_od = True
            return ClusterType.ON_DEMAND

        # Otherwise, before the fallback threshold:
        # Prefer Spot when available; avoid toggling to OD unnecessarily (choose NONE when Spot unavailable).
        if has_spot:
            return ClusterType.SPOT

        # Spot not available and we still have enough slack; wait (NONE) to avoid restart overhead churn.
        return ClusterType.NONE