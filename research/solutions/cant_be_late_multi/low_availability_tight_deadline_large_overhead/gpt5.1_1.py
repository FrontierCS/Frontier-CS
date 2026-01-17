import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType

try:
    CT_NONE = ClusterType.NONE
except AttributeError:
    CT_NONE = ClusterType.None


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy focusing on deadline guarantee with low cost."""

    NAME = "cant_be_late_multi_region_simple_v1"

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

        # Cached cumulative work done (seconds)
        self._accumulated_work_done = 0.0
        self._last_task_done_len = 0

        # Commit to on-demand once slack vs guaranteed on-demand run
        # is at most one time step (in seconds).
        gap = getattr(self.env, "gap_seconds", 1.0)
        self._commit_slack_threshold = float(gap) if gap > 0.0 else 1.0

        # Ensure restart_overhead is a scalar in seconds
        overhead = getattr(self, "restart_overhead", 0.0)
        if not isinstance(overhead, (int, float)):
            try:
                overhead = float(overhead[0])
                self.restart_overhead = overhead
            except Exception:
                try:
                    self.restart_overhead = float(overhead)
                except Exception:
                    self.restart_overhead = 0.0

        self._commit_to_on_demand = False
        return self

    def _update_work_done_cache(self) -> None:
        """Incrementally track total successful work time."""
        segments = getattr(self, "task_done_time", ())
        n = len(segments)
        if n > self._last_task_done_len:
            total_new = 0.0
            for i in range(self._last_task_done_len, n):
                total_new += segments[i]
            self._accumulated_work_done += total_new
            self._last_task_done_len = n

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update cached progress
        self._update_work_done_cache()

        # If task is already complete, stop using any cluster
        if self._accumulated_work_done >= self.task_duration:
            return CT_NONE

        now = self.env.elapsed_seconds
        time_left = self.deadline - now
        if time_left <= 0.0:
            # Deadline passed or exactly at deadline: best-effort on-demand
            return ClusterType.ON_DEMAND

        remaining_work = self.task_duration - self._accumulated_work_done
        if remaining_work < 0.0:
            remaining_work = 0.0

        # Decide when to irrevocably switch to On-Demand
        if not self._commit_to_on_demand:
            # Time needed to finish on On-Demand from now, including overhead
            if last_cluster_type == ClusterType.ON_DEMAND:
                future_overhead = getattr(self, "remaining_restart_overhead", 0.0)
            else:
                future_overhead = self.restart_overhead

            if future_overhead < 0.0:
                future_overhead = 0.0

            t_needed_on_demand = remaining_work + future_overhead
            slack_vs_od = time_left - t_needed_on_demand

            # Commit when remaining slack is at most one step, to avoid missing deadline
            if slack_vs_od <= self._commit_slack_threshold:
                self._commit_to_on_demand = True

        if self._commit_to_on_demand:
            return ClusterType.ON_DEMAND

        # Spot-preference phase: use Spot when available, otherwise wait to save cost
        if has_spot:
            return ClusterType.SPOT

        return CT_NONE