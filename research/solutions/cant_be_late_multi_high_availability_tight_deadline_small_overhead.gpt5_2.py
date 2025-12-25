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
        # Internal state for efficient progress tracking and control
        self._work_done_seconds = 0.0
        self._task_done_list_len = 0
        self._committed_to_od = False
        self._initialized = True
        return self

    def _update_work_done(self):
        # Incremental update to avoid O(n) sum every step
        curr_len = len(self.task_done_time)
        if curr_len > self._task_done_list_len:
            added = 0.0
            # Sum only new segments
            for i in range(self._task_done_list_len, curr_len):
                added += self.task_done_time[i]
            self._work_done_seconds += added
            self._task_done_list_len = curr_len

    def _remaining_work(self) -> float:
        self._update_work_done()
        remaining = self.task_duration - self._work_done_seconds
        return remaining if remaining > 0.0 else 0.0

    def _should_commit_to_on_demand(self) -> bool:
        # Decide whether we must switch to On-Demand to guarantee finishing by deadline.
        # Conservative threshold accounts for one restart overhead and one time step rounding.
        time_left = self.deadline - self.env.elapsed_seconds
        if time_left <= 0:
            return True
        remaining_work = self._remaining_work()
        # Conservative fudge: one time step to account for discretization and scheduling effects
        fudge = self.env.gap_seconds
        required_time_if_start_od_now = remaining_work + self.restart_overhead + fudge
        return time_left <= required_time_if_start_od_now

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If already done, just return NONE
        if self._remaining_work() <= 0.0:
            return ClusterType.NONE

        # Once committed to on-demand, stick to it to avoid extra overhead and risk.
        if not self._committed_to_od and self._should_commit_to_on_demand():
            self._committed_to_od = True

        if self._committed_to_od:
            return ClusterType.ON_DEMAND

        # Not committed to on-demand yet: use Spot when available
        if has_spot:
            return ClusterType.SPOT

        # Spot not available; if we still have slack, wait and explore other regions
        # by moving to the next region in a round-robin manner.
        # If time is too tight (handled above by commit check), we'd have committed to OD.
        num_regions = self.env.get_num_regions()
        if num_regions > 1:
            next_region = (self.env.get_current_region() + 1) % num_regions
            # Switch region only when idling to avoid losing productive work
            self.env.switch_region(next_region)

        return ClusterType.NONE
