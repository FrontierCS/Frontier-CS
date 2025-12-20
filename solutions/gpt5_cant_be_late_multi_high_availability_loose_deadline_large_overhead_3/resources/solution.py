import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_multi_v1"

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
        self._initialized = False
        self._od_committed = False
        self._wait_steps = 0
        self._num_regions = 1
        self._spot_obs = []
        self._obs = []
        return self

    def _initialize_if_needed(self):
        if self._initialized:
            return
        try:
            self._num_regions = self.env.get_num_regions()
        except Exception:
            self._num_regions = 1
        if self._num_regions is None or self._num_regions <= 0:
            self._num_regions = 1
        self._spot_obs = [0] * self._num_regions
        self._obs = [0] * self._num_regions
        self._initialized = True

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._initialize_if_needed()

        # Update observations for current region
        cur_region = self.env.get_current_region()
        if 0 <= cur_region < self._num_regions:
            self._obs[cur_region] += 1
            if has_spot:
                self._spot_obs[cur_region] += 1

        # Time accounting
        gap = float(getattr(self.env, "gap_seconds", 1.0))
        done = float(sum(self.task_done_time))
        remaining_work = max(0.0, float(self.task_duration) - done)
        if remaining_work <= 0.0:
            return ClusterType.NONE

        elapsed = float(self.env.elapsed_seconds)
        time_left = float(self.deadline) - elapsed
        if time_left <= 0.0:
            self._od_committed = True
            return ClusterType.ON_DEMAND

        restart = float(self.restart_overhead)

        # Commit to On-Demand if we are in the must-run window
        if time_left <= remaining_work + restart:
            self._od_committed = True

        if self._od_committed:
            self._wait_steps = 0
            return ClusterType.ON_DEMAND

        # Prefer Spot whenever available and not committed to OD
        if has_spot:
            self._wait_steps = 0
            return ClusterType.SPOT

        # Spot not available: decide to wait or switch to On-Demand
        # If we can't afford to wait one more step (gap), commit to On-Demand
        if time_left <= remaining_work + restart + gap:
            self._od_committed = True
            self._wait_steps = 0
            return ClusterType.ON_DEMAND

        # We can wait safely; try to reposition to search for Spot
        self._wait_steps += 1
        if self._num_regions > 1:
            # Simple round-robin search across regions while waiting
            next_region = (cur_region + 1) % self._num_regions
            if next_region != cur_region:
                self.env.switch_region(next_region)

        return ClusterType.NONE
