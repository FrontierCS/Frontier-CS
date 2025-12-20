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

        # Internal state initialization
        # Determine the "NONE" enum value robustly
        if hasattr(ClusterType, "NONE"):
            self.CLUSTER_NONE = ClusterType.NONE
        else:
            self.CLUSTER_NONE = ClusterType.None  # type: ignore[attr-defined]

        # Convert to seconds (MultiRegionStrategy should already do this,
        # but we store local aliases for clarity and speed).
        self.total_task = float(self.task_duration)
        self.overhead = float(self.restart_overhead)
        self.deadline_time = float(self.deadline)
        self.gap = float(self.env.gap_seconds)

        # Initial slack (seconds)
        self.initial_slack = self.deadline_time - self.total_task

        # Running sum for task_done_time to avoid O(n) per step
        self._work_done_sum = 0.0
        self._last_task_done_len = 0

        # Once we commit to on-demand, never go back to spot
        self._commit_to_on_demand = False

        # Slack threshold (in seconds) beyond remaining work at which we
        # must commit to ON_DEMAND to still safely finish.
        # Derivation: We can afford at most one full gap of zero progress
        # (idle or failed spot) and still switch to ON_DEMAND and finish.
        # Condition: time_left - gap >= remaining_work + overhead
        # => slack >= gap + overhead
        self._slack_commit_threshold = self.overhead + self.gap

        return self

    def _update_work_done_sum(self) -> None:
        """Incrementally maintain the sum of task_done_time."""
        td_list = self.task_done_time
        length = len(td_list)
        if length > self._last_task_done_len:
            s = self._work_done_sum
            for i in range(self._last_task_done_len, length):
                s += td_list[i]
            self._work_done_sum = s
            self._last_task_done_len = length

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.

        Returns: ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        # Keep running sum of work done
        self._update_work_done_sum()

        remaining_work = self.total_task - self._work_done_sum
        if remaining_work <= 0:
            # Task complete: no need to spend more money.
            return self.CLUSTER_NONE

        current_time = float(self.env.elapsed_seconds)
        time_left = self.deadline_time - current_time

        if time_left <= 0:
            # Already at / past deadline; nothing sensible to do but avoid cost.
            return self.CLUSTER_NONE

        # Slack = extra time beyond remaining work
        slack = time_left - remaining_work

        # If we've already committed to on-demand, always stay on it
        if self._commit_to_on_demand:
            return ClusterType.ON_DEMAND

        # If slack is small enough that we cannot afford even one more
        # zero-progress step, commit to ON_DEMAND now.
        # Also, if slack is already less than overhead, even immediate
        # ON_DEMAND cannot guarantee success, but we still do our best.
        if slack <= self._slack_commit_threshold or slack <= self.overhead:
            self._commit_to_on_demand = True
            return ClusterType.ON_DEMAND

        # We still have enough slack to risk one more step of no progress.
        # Prefer SPOT when available; otherwise, idle (NONE) to save cost.
        if has_spot:
            return ClusterType.SPOT

        # Spot unavailable, but plenty of slack: wait for cheaper resources.
        return self.CLUSTER_NONE
