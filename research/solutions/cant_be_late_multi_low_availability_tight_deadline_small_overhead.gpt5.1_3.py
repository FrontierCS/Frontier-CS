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

        deadline_hours = float(config["deadline"])
        duration_hours = float(config["duration"])
        overhead_hours = float(config["overhead"])

        args = Namespace(
            deadline_hours=deadline_hours,
            task_duration_hours=[duration_hours],
            restart_overhead_hours=[overhead_hours],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)

        # Store core parameters in seconds for convenience.
        self.deadline = deadline_hours * 3600.0
        self.task_duration = duration_hours * 3600.0
        self.restart_overhead = overhead_hours * 3600.0

        # Pre-compute a slack threshold (seconds) at which we commit to On-Demand.
        initial_slack_seconds = max(self.deadline - self.task_duration, 0.0)
        base_threshold = max(0.25 * 3600.0, 2.0 * self.restart_overhead)
        # Never let the commit threshold exceed the initial slack (for generality).
        self.commit_slack_seconds = min(base_threshold, initial_slack_seconds * 0.9) if initial_slack_seconds > 0 else 0.0

        # Internal bookkeeping for accumulated work.
        self._accumulated_work = 0.0  # in seconds
        self._last_seen_done_len = 0

        # Whether we've irrevocably switched to always using On-Demand.
        self.committed_to_on_demand = False

        return self

    def _update_accumulated_work(self) -> None:
        """Incrementally track total completed work time."""
        td = getattr(self, "task_done_time", None)
        if td is None:
            return
        n = len(td)
        if n > self._last_seen_done_len:
            # Sum only the newly appended segments.
            self._accumulated_work += sum(td[self._last_seen_done_len:n])
            self._last_seen_done_len = n

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.

        Returns: ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        # Update our view of how much work has been completed.
        self._update_accumulated_work()

        remaining_work = max(self.task_duration - self._accumulated_work, 0.0)

        # If the task is already done, don't run anything.
        if remaining_work <= 0.0:
            self.committed_to_on_demand = True
            return ClusterType.NONE

        elapsed = getattr(self.env, "elapsed_seconds", 0.0)
        remaining_time = self.deadline - elapsed
        slack = remaining_time - remaining_work

        # If we are not yet committed but slack is low, switch permanently to On-Demand.
        if (not self.committed_to_on_demand) and (slack <= self.commit_slack_seconds):
            self.committed_to_on_demand = True

        if self.committed_to_on_demand:
            # Once committed, always use On-Demand to guarantee completion.
            return ClusterType.ON_DEMAND

        # Pre-commit phase: prefer Spot when available; otherwise, wait (NONE) to save cost.
        if has_spot:
            return ClusterType.SPOT
        else:
            return ClusterType.NONE