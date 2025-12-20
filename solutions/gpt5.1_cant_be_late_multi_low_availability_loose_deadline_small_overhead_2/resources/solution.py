import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "my_strategy"  # REQUIRED: unique identifier

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the solution from spec_path config.

        The spec file contains:
        - deadline: deadline in hours
        - duration: task duration in hours
        - overhead: restart overhead in hours
        - trace_files: list of trace file paths (one per region)
        """
        with open(spec_path) as f:
            config = json.load(f)

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)

        # Strategy-specific state initialization
        self._work_done = 0.0
        # Index into task_done_time we've already accounted for
        try:
            self._last_task_done_index = len(self.task_done_time)
        except AttributeError:
            self.task_done_time = []
            self._last_task_done_index = 0

        # Flag indicating we've permanently switched to on-demand
        self._committed_to_on_demand = False

        # Conservative upper bound on extra elapsed time a single non-OD decision can cause
        gap = float(getattr(self.env, "gap_seconds", 0.0))
        self._delta_t_max = gap + float(self.restart_overhead)

        # Cache scalar versions of task_duration and deadline in seconds
        self._task_duration = float(self.task_duration)
        self._deadline = float(self.deadline)

        return self

    def _update_work_done(self) -> None:
        """Incrementally track total completed work to keep _step O(1)."""
        task_done_time = self.task_done_time
        last_idx = self._last_task_done_index
        n = len(task_done_time)
        if n > last_idx:
            total_new = 0.0
            for i in range(last_idx, n):
                total_new += task_done_time[i]
            self._work_done += total_new
            self._last_task_done_index = n

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        # Update running total of work completed.
        self._update_work_done()

        # If the task is already finished, do nothing.
        if self._work_done >= self._task_duration:
            return ClusterType.NONE

        # If we've already committed to on-demand, keep using it.
        if self._committed_to_on_demand:
            return ClusterType.ON_DEMAND

        # Compute remaining work and time left.
        remaining_work = self._task_duration - self._work_done
        time_left = self._deadline - self.env.elapsed_seconds

        # Slack time if we immediately switch to on-demand:
        # buffer = time_left - (restart_overhead + remaining_work)
        buffer = time_left - (self.restart_overhead + remaining_work)

        # If buffer is small, we must commit to on-demand now to guarantee meeting deadline.
        if buffer <= self._delta_t_max:
            self._committed_to_on_demand = True
            return ClusterType.ON_DEMAND

        # Otherwise, safely use cheap Spot if available; otherwise, wait.
        if has_spot:
            return ClusterType.SPOT
        return ClusterType.NONE
