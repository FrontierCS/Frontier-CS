import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cbl_multi_v1"

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
        self._done_seconds = 0.0
        self._done_list_len = 0
        self._committed_od = False
        return self

    def _update_done_seconds(self):
        # Incremental update to avoid summing the full list every step
        if self.task_done_time is None:
            return
        cur_len = len(self.task_done_time)
        if cur_len > self._done_list_len:
            # Add only the new entries
            for i in range(self._done_list_len, cur_len):
                self._done_seconds += self.task_done_time[i]
            self._done_list_len = cur_len

    def _should_commit_on_demand(self, last_cluster_type: ClusterType) -> bool:
        # Compute whether we must switch to On-Demand to meet the deadline
        self._update_done_seconds()

        remaining_work = max(self.task_duration - self._done_seconds, 0.0)
        time_left = self.deadline - self.env.elapsed_seconds

        # If already committed, stay with OD
        if self._committed_od:
            return True

        # Overhead to switch to OD; zero if we are already on OD
        overhead_if_switch = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else self.restart_overhead

        # Safety margin to account for discretization and overhead uncertainties
        gap = float(self.env.gap_seconds)
        margin = gap + 2.0 * self.restart_overhead + 30.0  # seconds

        required_time = overhead_if_switch + remaining_work
        return required_time >= (time_left - margin)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Ensure progress tracking is up-to-date
        self._update_done_seconds()

        # If we must commit to On-Demand to meet the deadline, do so
        if self._should_commit_on_demand(last_cluster_type):
            self._committed_od = True
            return ClusterType.ON_DEMAND

        # Prefer Spot when available
        if has_spot:
            return ClusterType.SPOT

        # Otherwise, wait to save cost and try another region opportunistically
        num_regions = self.env.get_num_regions()
        if num_regions > 1:
            next_region = (self.env.get_current_region() + 1) % num_regions
            self.env.switch_region(next_region)
        return ClusterType.NONE