import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "safe_spot_multi_v2"

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

        # Internal state initialization
        self._inited = False
        self._committed_to_od = False
        self._last_done_len = 0
        self._done_sum = 0.0
        self._alpha = 0.1
        self._num_regions = None
        self._est_prob = None
        self._region_visit_counts = None
        self._last_known_spot = None

        return self

    def _lazy_init(self):
        if not self._inited:
            n = self.env.get_num_regions()
            self._num_regions = n
            self._est_prob = [0.5] * n
            self._region_visit_counts = [0] * n
            self._last_known_spot = [0] * n
            self._inited = True

    def _update_progress_sum(self):
        # Incrementally update the sum of task_done_time
        cur_len = len(self.task_done_time)
        if cur_len > self._last_done_len:
            # Sum only the new elements
            new_sum = 0.0
            for i in range(self._last_done_len, cur_len):
                new_sum += self.task_done_time[i]
            self._done_sum += new_sum
            self._last_done_len = cur_len

    def _update_region_stats(self, has_spot: bool):
        # Update EMA of availability for the current region
        rid = self.env.get_current_region()
        self._region_visit_counts[rid] += 1
        cur_est = self._est_prob[rid]
        self._est_prob[rid] = (1.0 - self._alpha) * cur_est + self._alpha * (1.0 if has_spot else 0.0)
        self._last_known_spot[rid] = 1 if has_spot else 0

    def _best_region(self):
        # Choose region with highest estimated spot availability
        rid = self.env.get_current_region()
        best_idx = rid
        best_val = self._est_prob[rid]
        for i in range(self._num_regions):
            if self._est_prob[i] > best_val + 1e-12:
                best_val = self._est_prob[i]
                best_idx = i
        return best_idx

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._lazy_init()
        self._update_progress_sum()

        # If already done, no need to run
        remaining_work = self.task_duration - self._done_sum
        if remaining_work <= 0.0:
            return ClusterType.NONE

        # Update region statistics with current observed spot availability
        self._update_region_stats(has_spot)

        # If we are already on on-demand, keep running on-demand to avoid additional overhead and risk
        if last_cluster_type == ClusterType.ON_DEMAND or self._committed_to_od:
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        gap = self.env.gap_seconds
        time_left = self.deadline - self.env.elapsed_seconds

        # Latest safe start logic:
        # To be safe even if we waste the entire next step (gap) on spot due to preemption,
        # we need to ensure we can still finish with ON_DEMAND (including one restart overhead).
        # Commit to ON_DEMAND when time_left is tight.
        required_time_with_od_if_start_later = remaining_work + self.restart_overhead

        # Commit margin: one step gap to cover worst-case lost step if we try spot and get nothing
        commit_margin = gap

        # If time is too tight, commit to ON_DEMAND now
        if time_left <= required_time_with_od_if_start_later + commit_margin:
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        # Otherwise, we have enough slack to try SPOT if available
        if has_spot:
            return ClusterType.SPOT

        # Spot not available: if we still have enough slack to wait one step, pause and switch to best region
        if time_left > required_time_with_od_if_start_later + commit_margin:
            # Switch to the region with highest estimated availability for the next step
            best_r = self._best_region()
            if best_r != self.env.get_current_region():
                self.env.switch_region(best_r)
            return ClusterType.NONE

        # Fallback: commit to ON_DEMAND to ensure completion
        self._committed_to_od = True
        return ClusterType.ON_DEMAND