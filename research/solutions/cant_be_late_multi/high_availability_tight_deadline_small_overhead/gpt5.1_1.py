import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy that prioritizes cheap Spot instances
    while guaranteeing completion before the deadline by switching to On-Demand
    when necessary.
    """

    NAME = "cant_be_late_v1"

    def solve(self, spec_path: str) -> "Solution":
        """Initialize the solution from spec_path config."""
        with open(spec_path) as f:
            config = json.load(f)

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)

        # Internal state for incremental progress tracking
        self._progress_sec = 0.0
        self._last_task_done_count = 0

        # Whether we've irrevocably switched to only using On-Demand
        self._committed_to_ondemand = False
        self._commit_time = None
        return self

    @staticmethod
    def _scalar(value):
        """Convert a possibly list-valued attribute into a scalar float."""
        if isinstance(value, (list, tuple)):
            if not value:
                return 0.0
            return float(value[0])
        return float(value)

    def _update_progress(self):
        """Incrementally update cached progress from task_done_time."""
        td_list = getattr(self, "task_done_time", None)

        # Handle None or empty list
        if not td_list:
            # If previously non-zero, reset to actual (which is zero here)
            self._progress_sec = 0.0
            self._last_task_done_count = 0
            return

        current_len = len(td_list)

        # List shrank unexpectedly (very rare): recompute from scratch
        if current_len < self._last_task_done_count:
            total = 0.0
            for v in td_list:
                if isinstance(v, (list, tuple)):
                    for inner in v:
                        total += float(inner)
                else:
                    total += float(v)
            self._progress_sec = total
            self._last_task_done_count = current_len
            return

        # New segments appended: accumulate only the new ones
        if current_len > self._last_task_done_count:
            total_new = 0.0
            for v in td_list[self._last_task_done_count:current_len]:
                if isinstance(v, (list, tuple)):
                    for inner in v:
                        total_new += float(inner)
                else:
                    total_new += float(v)
            self._progress_sec += total_new
            self._last_task_done_count = current_len

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """Decide next action: Spot, On-Demand, or None."""
        # Defensive initialization in case solve() wasn't called (shouldn't happen)
        if not hasattr(self, "_progress_sec"):
            self._progress_sec = 0.0
            self._last_task_done_count = 0
            self._committed_to_ondemand = False
            self._commit_time = None

        # Update progress based on environment-reported completed segments
        self._update_progress()
        progress = self._progress_sec

        # Convert environment parameters to scalar seconds
        task_duration = self._scalar(getattr(self, "task_duration", 0.0))
        deadline = self._scalar(getattr(self, "deadline", 0.0))
        restart_overhead = self._scalar(getattr(self, "restart_overhead", 0.0))
        gap_seconds = float(getattr(self.env, "gap_seconds", 0.0))
        elapsed_seconds = float(getattr(self.env, "elapsed_seconds", 0.0))

        remaining_work = max(task_duration - progress, 0.0)
        time_left = deadline - elapsed_seconds

        # If task already completed, do nothing.
        if remaining_work <= 0.0:
            return ClusterType.NONE

        # If we've already committed to On-Demand, always use it.
        if self._committed_to_ondemand:
            return ClusterType.ON_DEMAND

        # If somehow past the deadline, just finish as cheaply as possible.
        if time_left <= 0.0:
            # This case should be rare; deadline miss penalty is already incurred.
            if has_spot:
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND

        # Safety buffer to account for discrete time steps and minor modeling errors.
        # We choose a conservative buffer: at least one step or one restart_overhead.
        safety_buffer = max(gap_seconds, restart_overhead)

        # Assume switching to On-Demand will cost at most one restart_overhead from now.
        overhead_to_ondemand = restart_overhead

        # Guarantee-feasible commit rule:
        # If the remaining time is no more than the time needed to finish entirely on
        # On-Demand (remaining_work + overhead) plus a small buffer, we must switch
        # now to ensure we finish before the deadline in the worst case.
        if time_left <= remaining_work + overhead_to_ondemand + safety_buffer:
            self._committed_to_ondemand = True
            self._commit_time = elapsed_seconds
            return ClusterType.ON_DEMAND

        # In the "early" phase we prioritize cost:
        # - Use Spot whenever it's available.
        # - Otherwise, pause (NONE) and rely on future Spot or eventual On-Demand commit.
        if has_spot:
            return ClusterType.SPOT
        else:
            return ClusterType.NONE