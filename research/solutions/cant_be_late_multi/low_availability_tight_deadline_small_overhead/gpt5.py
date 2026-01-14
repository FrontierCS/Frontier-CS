import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "deadline_safe_spot_waiter_v1"

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

        # Internal trackers for efficient progress computation and commitment state
        self._accum_done = 0.0
        self._prev_task_done_len = 0
        self._commit_on_demand = False
        return self

    def _update_progress_cache(self):
        # Incrementally accumulate done work to avoid O(n) sum per step
        cur_len = len(self.task_done_time)
        if cur_len > self._prev_task_done_len:
            # Only sum new segments
            added = 0.0
            for i in range(self._prev_task_done_len, cur_len):
                added += self.task_done_time[i]
            self._accum_done += added
            self._prev_task_done_len = cur_len

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If already committed to on-demand, keep using it until finish
        if self._commit_on_demand:
            return ClusterType.ON_DEMAND

        self._update_progress_cache()

        # Remaining work in seconds
        remaining = max(0.0, self.task_duration - self._accum_done)
        if remaining <= 0.0:
            return ClusterType.NONE

        # Time parameters
        gap = getattr(self.env, "gap_seconds", 300.0)
        if gap <= 0:
            gap = 300.0
        slack = self.deadline - self.env.elapsed_seconds

        # Time needed to finish on on-demand if we switch now
        # If currently on on-demand, no additional switch overhead; otherwise pay restart overhead once.
        need_overhead = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else self.restart_overhead
        od_time_needed_now = remaining + need_overhead

        # Safe guard: to ensure we can always switch to OD next step even if we make zero progress this step,
        # we must maintain at least an extra 'gap' seconds of slack.
        # Commit to OD if slack is not enough for another step of potential no-progress.
        if slack <= od_time_needed_now + gap:
            self._commit_on_demand = True
            return ClusterType.ON_DEMAND

        # Otherwise, be cost-efficient:
        # - Use Spot if available.
        # - If Spot is unavailable, wait (NONE) to save cost as long as we're within safety window.
        if has_spot:
            return ClusterType.SPOT

        return ClusterType.NONE