import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Cant-Be-Late multi-region scheduling strategy."""

    NAME = "cant_be_late_slack_v1"

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
        self._cached_work_done = 0.0
        self._last_task_done_index = 0
        self._fallback_committed = False

        return self

    def _update_work_done_cache(self) -> None:
        """Incrementally cache total completed work to avoid O(n^2) summation."""
        td = self.task_done_time
        n = len(td)
        if n > self._last_task_done_index:
            total = self._cached_work_done
            start = self._last_task_done_index
            for i in range(start, n):
                total += td[i]
            self._cached_work_done = total
            self._last_task_done_index = n

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update cached progress
        self._update_work_done_cache()
        work_done = self._cached_work_done

        # Remaining work
        work_left = self.task_duration - work_done
        if work_left <= 0:
            # Task completed
            return ClusterType.NONE

        elapsed = self.env.elapsed_seconds
        time_left = self.deadline - elapsed

        if time_left <= 0:
            # Already past deadline; minimize lateness with on-demand
            self._fallback_committed = True
            return ClusterType.ON_DEMAND

        # If we've already switched to on-demand, stay there
        if self._fallback_committed:
            return ClusterType.ON_DEMAND

        # Estimate conservative overhead if we switch to on-demand now
        overhead_now = self.restart_overhead
        rem_overhead = getattr(self, "remaining_restart_overhead", 0.0)
        if rem_overhead > overhead_now:
            overhead_now = rem_overhead

        step = self.env.gap_seconds

        # Fallback condition: ensure we can waste at most one more step and
        # still have time for overhead + remaining work on on-demand.
        if time_left <= work_left + overhead_now + step:
            self._fallback_committed = True
            return ClusterType.ON_DEMAND

        # Pre-fallback: use Spot when available, otherwise wait (NONE)
        if has_spot:
            return ClusterType.SPOT

        return ClusterType.NONE
