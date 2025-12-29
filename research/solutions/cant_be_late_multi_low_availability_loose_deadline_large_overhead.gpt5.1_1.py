import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy focusing on deadline safety and cost minimization."""

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

        # Internal state for efficient accounting and decisions
        self._cached_done_time = 0.0
        self._last_task_done_len = 0
        self._commit_to_on_demand = False

        # Cache ClusterType members in a robust way
        self._spot_type = getattr(ClusterType, "SPOT")
        self._on_demand_type = getattr(ClusterType, "ON_DEMAND")
        none_attr = "NONE" if hasattr(ClusterType, "NONE") else "None"
        self._none_type = getattr(ClusterType, none_attr)

        return self

    def _update_cached_progress(self) -> float:
        """Incrementally track total completed work time."""
        segments = self.task_done_time
        current_len = len(segments)
        if current_len != self._last_task_done_len:
            total_new = 0.0
            # Sum only the newly added segments
            for i in range(self._last_task_done_len, current_len):
                total_new += segments[i]
            self._cached_done_time += total_new
            self._last_task_done_len = current_len
        return self._cached_done_time

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update total work done efficiently
        work_done = self._update_cached_progress()
        remaining_work = self.task_duration - work_done
        if remaining_work <= 0.0:
            # Task is effectively complete; no need to run more
            return self._none_type

        t = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        restart = self.restart_overhead
        deadline = self.deadline

        # Worst-case completion time if we spend one more step making no progress
        # (either using SPOT that fails or idling) and then switch to ON_DEMAND.
        worst_future_completion_if_wait = t + gap + restart + remaining_work

        # Decide if we must now irrevocably switch to ON_DEMAND to make the deadline.
        if not self._commit_to_on_demand:
            if worst_future_completion_if_wait > deadline:
                # Last moment to safely commit to on-demand-only plan
                self._commit_to_on_demand = True

        if self._commit_to_on_demand:
            # From this point on, always use On-Demand until completion.
            return self._on_demand_type

        # Still in the flexible phase where we can exploit Spot or idle.
        if has_spot:
            # Prefer Spot when available while we still have enough slack.
            return self._spot_type

        # No Spot available. If we're still before the commit threshold,
        # it is cheaper to wait than to use expensive On-Demand.
        return self._none_type