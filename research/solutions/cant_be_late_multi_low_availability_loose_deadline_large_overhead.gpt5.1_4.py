import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "cant_be_late_spot_first"

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

        # Internal scalar parameters (seconds)
        self._task_duration_total = self._to_scalar(self.task_duration)
        self._restart_overhead = self._to_scalar(self.restart_overhead)

        # Tracking progress efficiently
        self._total_work_done = 0.0
        self._last_task_done_len = 0

        # Once we commit to on-demand, never go back to spot
        self._committed_to_on_demand = False

        # Safety margin to account for discrete time steps
        gap = getattr(self.env, "gap_seconds", 1.0)
        # Commit when remaining slack is below this many seconds
        self._commit_margin = gap * 2.0

        return self

    def _to_scalar(self, x):
        try:
            return float(x)
        except TypeError:
            return float(x[0])

    def _update_progress(self):
        """Incrementally track total work done without O(n^2) summations."""
        td = self.task_done_time
        cur_len = len(td)
        if cur_len > self._last_task_done_len:
            inc = 0.0
            for i in range(self._last_task_done_len, cur_len):
                inc += float(td[i])
            self._total_work_done += inc
            self._last_task_done_len = cur_len

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update cached work done
        self._update_progress()

        # If task already complete, no need to run more
        if self._total_work_done >= self._task_duration_total:
            return ClusterType.NONE

        elapsed = self.env.elapsed_seconds
        time_remaining = self.deadline - elapsed

        # If somehow past deadline, just use on-demand (nothing else helps)
        if time_remaining <= 0:
            return ClusterType.ON_DEMAND

        remaining_work = self._task_duration_total - self._total_work_done
        if remaining_work < 0.0:
            remaining_work = 0.0

        # If we have already committed, always use on-demand
        if self._committed_to_on_demand:
            return ClusterType.ON_DEMAND

        # Worst-case time needed if we switch to on-demand now:
        # one restart overhead + remaining work (on-demand never interrupted)
        required_time_if_commit_now = remaining_work + self._restart_overhead
        slack = time_remaining - required_time_if_commit_now

        # Commit to on-demand when slack is small to guarantee meeting deadline
        if slack <= self._commit_margin:
            self._committed_to_on_demand = True
            return ClusterType.ON_DEMAND

        # Not yet committed: use spot when available, otherwise idle
        if has_spot:
            return ClusterType.SPOT
        else:
            return ClusterType.NONE
