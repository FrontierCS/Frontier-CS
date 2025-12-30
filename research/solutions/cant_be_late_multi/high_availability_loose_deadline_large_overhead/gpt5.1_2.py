import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy with deadline guarantee and cost awareness."""

    NAME = "cant_be_late_multi_region_strategy"

    def solve(self, spec_path: str) -> "Solution":
        # Load config
        with open(spec_path) as f:
            config = json.load(f)

        # Initialize parent strategy (creates env, converts to seconds internally)
        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)

        # Store parameters in seconds (from config, independent of parent internals)
        self._deadline_total = float(config["deadline"]) * 3600.0
        self._task_duration_total = float(config["duration"]) * 3600.0
        self._restart_overhead_total = float(config["overhead"]) * 3600.0

        # Gap seconds from environment; if unavailable, default to 0.0
        self._gap_seconds = float(getattr(self.env, "gap_seconds", 0.0))

        # Maximum potential drop in "safety slack" g per step:
        # g = time_left - (remaining_work + restart_overhead)
        # In worst case we lose at most gap + restart_overhead in one step.
        self._safe_margin = self._gap_seconds + self._restart_overhead_total

        # Track cumulative work done without O(n^2) summations
        self._work_done = 0.0
        self._last_task_done_len = 0

        # Once we flip this, we stick to ON_DEMAND until completion
        self._committed_on_demand = False

        return self

    def _update_work_done(self) -> None:
        """Incrementally update cumulative work done from task_done_time list."""
        current_len = len(self.task_done_time)
        if current_len > self._last_task_done_len:
            # Sum only new segments
            new_segments = self.task_done_time[self._last_task_done_len:current_len]
            # Using built-in sum is fine here; each segment is summed once overall.
            self._work_done += sum(new_segments)
            self._last_task_done_len = current_len

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update cached progress
        self._update_work_done()

        # If we already committed to ON_DEMAND, never go back or switch regions.
        if self._committed_on_demand:
            return ClusterType.ON_DEMAND

        # Compute time left and remaining work in seconds
        elapsed = float(self.env.elapsed_seconds)
        time_left = self._deadline_total - elapsed

        # If somehow time_left is non-positive, just run ON_DEMAND (env may handle failure)
        if time_left <= 0.0:
            self._committed_on_demand = True
            return ClusterType.ON_DEMAND

        remaining_work = max(self._task_duration_total - self._work_done, 0.0)

        # Safety slack g: how much extra time we have beyond what's needed
        # to finish all remaining work plus one restart overhead if we switch to OD now.
        g = time_left - (remaining_work + self._restart_overhead_total)

        # If our safety slack is getting close to the worst possible one-step drop,
        # immediately commit to ON_DEMAND to guarantee completion by deadline.
        if g < self._safe_margin:
            self._committed_on_demand = True
            return ClusterType.ON_DEMAND

        # Still in the "explore / cheap" phase: prefer SPOT when available, else idle.
        if has_spot:
            return ClusterType.SPOT

        # Spot unavailable in current region; idle to save cost while we still have slack.
        return ClusterType.NONE