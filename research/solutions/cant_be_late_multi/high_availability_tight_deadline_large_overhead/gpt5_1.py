import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "my_strategy"

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
        self._od_committed = False
        return self

    def _ensure_internal_state(self):
        # Lazily initialize any state that depends on environment
        if not hasattr(self, "_initialized"):
            self._initialized = True

    def _work_remaining(self) -> float:
        done = sum(self.task_done_time) if self.task_done_time else 0.0
        return max(0.0, self.task_duration - done)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_internal_state()

        # If already committed to On-Demand, keep using it
        if getattr(self, "_od_committed", False):
            return ClusterType.ON_DEMAND

        # Compute remaining work and time
        remaining_work = self._work_remaining()
        if remaining_work <= 0.0:
            return ClusterType.NONE

        time_left = self.deadline - self.env.elapsed_seconds
        gap = self.env.gap_seconds
        restart_overhead = self.restart_overhead

        # Safe threshold to guarantee finishing on OD if we commit now
        od_time_needed = remaining_work + restart_overhead

        # If we already don't have enough time for OD safety margin, immediately commit
        if time_left <= od_time_needed:
            self._od_committed = True
            return ClusterType.ON_DEMAND

        # Prefer Spot when available and we have slack
        if has_spot:
            return ClusterType.SPOT

        # Spot not available: decide to wait, switch region, or commit to OD
        # Only wait (ClusterType.NONE) if we have at least one more full step of slack above OD requirement
        # This ensures that after waiting one step, we can still switch to OD and finish in time.
        if time_left > od_time_needed + gap:
            # Try another region next to hunt for availability
            num_regions = self.env.get_num_regions()
            if num_regions > 1:
                next_region = (self.env.get_current_region() + 1) % num_regions
                self.env.switch_region(next_region)
            return ClusterType.NONE

        # Not enough slack to wait; commit to OD now
        self._od_committed = True
        return ClusterType.ON_DEMAND