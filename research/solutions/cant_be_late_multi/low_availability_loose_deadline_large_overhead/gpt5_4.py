import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_guarded"

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
        self._cached_done_sum = 0.0
        self._cached_done_len = 0
        self._committed_on_demand = False
        return self

    # ----------------------- Internal helpers -----------------------

    def _ensure_init(self):
        if self._initialized:
            return
        num_regions = self.env.get_num_regions()
        self._region_seen = [0] * num_regions
        self._region_spot_up = [0] * num_regions
        self._initialized = True

    def _update_region_stats(self, has_spot: bool):
        idx = self.env.get_current_region()
        self._region_seen[idx] += 1
        if has_spot:
            self._region_spot_up[idx] += 1

    def _get_total_done(self) -> float:
        # Efficiently maintain running sum
        if len(self.task_done_time) > self._cached_done_len:
            new_seg_sum = sum(self.task_done_time[self._cached_done_len :])
            self._cached_done_sum += new_seg_sum
            self._cached_done_len = len(self.task_done_time)
        return self._cached_done_sum

    def _choose_region_on_wait(self) -> int:
        # Simple round-robin to diversify chances across regions
        n = self.env.get_num_regions()
        if n <= 1:
            return self.env.get_current_region()
        return (self.env.get_current_region() + 1) % n

    # ----------------------- Decision Logic -------------------------

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_init()
        # Update stats about current region availability
        self._update_region_stats(has_spot)

        # If already committed to On-Demand, keep running OD to ensure finish
        if self._committed_on_demand:
            return ClusterType.ON_DEMAND

        # Time accounting
        now = self.env.elapsed_seconds
        time_remaining = self.deadline - now

        done = self._get_total_done()
        remaining_work = max(0.0, self.task_duration - done)

        # If we commit to OD now, how much time is needed (work + overhead)
        if self.env.cluster_type == ClusterType.ON_DEMAND:
            overhead_if_commit_now = self.remaining_restart_overhead
        else:
            overhead_if_commit_now = self.restart_overhead

        time_needed_by_od = remaining_work + max(0.0, overhead_if_commit_now)

        # Guard policy: must commit to OD if we cannot afford to lose another step
        # i.e., worst-case losing one more gap before switching to OD.
        if time_remaining <= time_needed_by_od + self.env.gap_seconds:
            self._committed_on_demand = True
            return ClusterType.ON_DEMAND

        # Otherwise, we can still chase Spot
        if has_spot:
            return ClusterType.SPOT

        # Spot unavailable: wait to save cost and switch region to search
        next_region = self._choose_region_on_wait()
        if next_region != self.env.get_current_region():
            self.env.switch_region(next_region)
        return ClusterType.NONE