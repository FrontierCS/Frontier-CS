import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy with hard-deadline guarantee."""

    NAME = "cant_be_late_safe_slack_v1"

    def __init__(self):
        # Defer MultiRegionStrategy initialization to solve().
        # Avoid requiring constructor arguments for the evaluator.
        self.env = None
        self.task_duration = 0.0
        self.deadline = 0.0
        self.restart_overhead = 0.0
        self.task_done_time = []
        self.remaining_restart_overhead = 0.0

        # Internal state
        self._work_done = 0.0
        self._last_task_done_len = 0
        self._commit_on_demand = False
        self._slack_threshold = 0.0

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the solution from spec_path config.
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

        # Initialize internal scheduling state.
        self._work_done = 0.0
        self._last_task_done_len = 0
        self._commit_on_demand = False

        # Slack threshold for switching to on-demand (in seconds).
        # At least one full time step plus one restart overhead for safety.
        gap = getattr(self.env, "gap_seconds", 0.0)
        overhead = float(self.restart_overhead)
        self._slack_threshold = gap + overhead

        return self

    def _update_work_done(self) -> None:
        """Incrementally accumulate completed work from task_done_time."""
        segments = self.task_done_time
        length = len(segments)
        if length > self._last_task_done_len:
            added = 0.0
            for i in range(self._last_task_done_len, length):
                added += segments[i]
            self._work_done += added
            self._last_task_done_len = length

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.

        Returns: ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        # Update accumulated work from environment.
        self._update_work_done()

        # If task is effectively finished, do not use any cluster.
        if self._work_done >= float(self.task_duration) - 1e-6:
            return ClusterType.NONE

        # Once we decide to switch to on-demand, stick with it until completion.
        if self._commit_on_demand:
            return ClusterType.ON_DEMAND

        now = float(self.env.elapsed_seconds)
        remaining_work = float(self.task_duration) - self._work_done
        if remaining_work < 0.0:
            remaining_work = 0.0

        overhead = float(self.restart_overhead)
        deadline = float(self.deadline)

        # Upper-bound estimate of finish time if we commit to on-demand now.
        finish_time_if_commit = now + overhead + remaining_work

        # If even committing now nearly reaches or exceeds the deadline,
        # immediately commit to on-demand (no further risk-taking).
        if finish_time_if_commit >= deadline - 1e-6:
            self._commit_on_demand = True
            return ClusterType.ON_DEMAND

        # Compute conservative slack under on-demand-from-now plan.
        slack = deadline - finish_time_if_commit

        # If slack is below threshold, start on-demand now to guarantee completion.
        if slack < self._slack_threshold:
            self._commit_on_demand = True
            return ClusterType.ON_DEMAND

        # Opportunistic phase: use Spot when available; otherwise, wait (NONE).
        if has_spot:
            return ClusterType.SPOT

        return ClusterType.NONE