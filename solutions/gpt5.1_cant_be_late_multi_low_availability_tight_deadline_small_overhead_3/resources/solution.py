import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Deadline-safe multi-region scheduling strategy (single-region use)."""

    NAME = "cant_be_late_mr_v1"

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

        # Strategy state
        self._committed_to_on_demand = False

        # Cached work-done tracking
        try:
            tdt = self.task_done_time
        except AttributeError:
            tdt = []
        self._prev_task_done_len = len(tdt)
        self._total_work_done = float(sum(tdt)) if tdt else 0.0

        # Precompute constants
        self._gap_seconds = float(getattr(self.env, "gap_seconds", 0.0))
        # restart_overhead is in seconds in the env after base init
        self._restart_overhead = float(getattr(self, "restart_overhead", 0.0))
        # Worst-case slack loss from one exploratory step (spot/idle)
        self._time_drop_max = self._gap_seconds + self._restart_overhead

        return self

    def _update_work_done_cache(self) -> None:
        """Incrementally track total work done to avoid O(n) summations each step."""
        tdt = self.task_done_time
        n = len(tdt)
        if n > self._prev_task_done_len:
            inc = 0.0
            for i in range(self._prev_task_done_len, n):
                inc += tdt[i]
            self._total_work_done += inc
            self._prev_task_done_len = n

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Refresh cached progress
        self._update_work_done_cache()

        # Remaining work and time
        remaining_work = self.task_duration - self._total_work_done
        if remaining_work <= 0:
            # Task completed; no further compute needed
            return ClusterType.NONE

        time_to_deadline = self.deadline - self.env.elapsed_seconds
        if time_to_deadline <= 0:
            # Deadline has passed; nothing sensible to do
            return ClusterType.NONE

        # Once we commit to on-demand, never go back to spot
        if self._committed_to_on_demand:
            return ClusterType.ON_DEMAND

        # Conservative slack if we immediately switch to on-demand from current state.
        # Use full restart_overhead as a safe worst-case, regardless of last_cluster_type.
        commit_overhead = self._restart_overhead
        slack_if_commit_now = time_to_deadline - commit_overhead - remaining_work

        # If slack is comparable to the maximum we can lose in one additional exploratory step,
        # switch to on-demand now to guarantee finishing before the deadline.
        if slack_if_commit_now <= self._time_drop_max:
            self._committed_to_on_demand = True
            return ClusterType.ON_DEMAND

        # Exploration phase: use spot when available (cheap), otherwise wait (NONE).
        if has_spot:
            return ClusterType.SPOT
        else:
            return ClusterType.NONE
