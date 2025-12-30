import json
from argparse import Namespace
from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cbl_rr_v3"

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
        return self

    def _lazy_init(self):
        if self._initialized:
            return
        self._initialized = True
        self._num_regions = self.env.get_num_regions()
        self._reg_seen = [0] * self._num_regions
        self._reg_true_cnt = [0] * self._num_regions
        self._reg_last_true_time = [-1.0] * self._num_regions

    def _pick_region_on_no_spot(self, current_region: int):
        # Prefer the region with the most recent known True availability.
        best_idx = -1
        best_time = -1.0
        for i in range(self._num_regions):
            if i == current_region:
                continue
            t = self._reg_last_true_time[i]
            if t > best_time:
                best_time = t
                best_idx = i
        if best_idx >= 0 and best_time >= 0.0:
            return best_idx
        # Fallback: round-robin
        return (current_region + 1) % self._num_regions

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._lazy_init()

        # Update region stats
        now = self.env.elapsed_seconds
        cur_region = self.env.get_current_region()
        if 0 <= cur_region < self._num_regions:
            self._reg_seen[cur_region] += 1
            if has_spot:
                self._reg_true_cnt[cur_region] += 1
                self._reg_last_true_time[cur_region] = now

        # If already finished, do nothing
        work_done = sum(self.task_done_time)
        remaining_work = max(0.0, self.task_duration - work_done)
        if remaining_work <= 0.0:
            return ClusterType.NONE

        gap = self.env.gap_seconds
        time_left = self.deadline - now
        eps = 1e-6

        # If already committed to on-demand, stick to it
        if self._od_committed:
            return ClusterType.ON_DEMAND

        # Time needed if we switch to OD now
        overhead_to_od = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else self.restart_overhead
        od_time_needed = remaining_work + overhead_to_od

        # Commit to OD if we no longer have buffer
        if time_left <= od_time_needed + eps:
            self._od_committed = True
            return ClusterType.ON_DEMAND

        # Prefer Spot if available and not urgent
        if has_spot:
            return ClusterType.SPOT

        # Spot not available in current region. Decide whether to wait, switch region, or use OD.
        # If we can afford to wait one step and still finish with OD afterwards, then wait (NONE) and try another region.
        # Otherwise, commit to OD now.
        if time_left - gap > (remaining_work + self.restart_overhead) + eps:
            # Try a different region next step
            if self._num_regions > 1:
                next_region = self._pick_region_on_no_spot(cur_region)
                if next_region != cur_region:
                    self.env.switch_region(next_region)
            return ClusterType.NONE
        else:
            self._od_committed = True
            return ClusterType.ON_DEMAND