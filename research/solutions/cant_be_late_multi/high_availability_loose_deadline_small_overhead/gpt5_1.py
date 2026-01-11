import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_mr_v1"

    def __init__(self):
        # Defer MultiRegionStrategy init to solve()
        super().__init__(Namespace(
            deadline_hours=0.0,
            task_duration_hours=[0.0],
            restart_overhead_hours=[0.0],
            inter_task_overhead=[0.0],
        ))
        # Internal state
        self._inited = False
        self._commit_od = False
        self._num_regions = 0
        self._progress_sum = 0.0
        self._progress_len_cache = 0
        self._region_seen = []
        self._region_up = []
        self._guard_time = 0.0

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
        # Reset internal state for a new environment
        self._inited = False
        self._commit_od = False
        self._num_regions = 0
        self._progress_sum = 0.0
        self._progress_len_cache = 0
        self._region_seen = []
        self._region_up = []
        self._guard_time = 0.0
        return self

    def _lazy_init(self):
        if self._inited:
            return
        self._num_regions = max(1, int(self.env.get_num_regions()))
        self._region_seen = [0] * self._num_regions
        self._region_up = [0] * self._num_regions
        # Guard time before switching to On-Demand to account for discretization and overheads
        # Choose a conservative buffer: two steps plus twice the restart overhead
        self._guard_time = 2.0 * float(self.env.gap_seconds) + 2.0 * float(self.restart_overhead)
        self._inited = True

    def _update_progress_cache(self):
        # Efficient incremental sum of task_done_time
        if self._progress_len_cache < len(self.task_done_time):
            added = sum(self.task_done_time[self._progress_len_cache:])
            self._progress_sum += added
            self._progress_len_cache = len(self.task_done_time)

    def _choose_next_region(self, current_region: int) -> int:
        # Deterministic round-robin to avoid heavy bookkeeping
        if self._num_regions <= 1:
            return current_region
        return (current_region + 1) % self._num_regions

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._lazy_init()
        self._update_progress_cache()

        # Remaining work and time
        remaining_work = max(self.task_duration - self._progress_sum, 0.0)
        remaining_time = max(self.deadline - self.env.elapsed_seconds, 0.0)

        # If done, don't run anything
        if remaining_work <= 0.0:
            return ClusterType.NONE

        # If we've already committed to On-Demand, continue
        if self._commit_od:
            return ClusterType.ON_DEMAND

        # Compute extra overhead if we switch to On-Demand now
        od_extra_overhead = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else self.restart_overhead

        # Allowed slack time beyond guaranteed OD completion
        allow = remaining_time - (remaining_work + od_extra_overhead)

        # If we don't have sufficient slack, commit to On-Demand
        if allow <= self._guard_time:
            self._commit_od = True
            return ClusterType.ON_DEMAND

        # Use spot if available in current region
        current_region = self.env.get_current_region()
        # Update region stats with observation
        self._region_seen[current_region] += 1
        if has_spot:
            self._region_up[current_region] += 1
            return ClusterType.SPOT

        # Spot not available: if we have enough slack, wait and try another region
        # Spend at most one step of waiting while leaving sufficient guard
        if allow > (self._guard_time + float(self.env.gap_seconds) * 0.5):
            next_region = self._choose_next_region(current_region)
            if next_region != current_region:
                self.env.switch_region(next_region)
            return ClusterType.NONE

        # Otherwise, switch to On-Demand to guarantee completion
        self._commit_od = True
        return ClusterType.ON_DEMAND