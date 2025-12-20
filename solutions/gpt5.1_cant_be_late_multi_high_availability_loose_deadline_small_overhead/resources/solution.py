import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType

try:
    CLUSTER_NONE = ClusterType.NONE
except AttributeError:
    CLUSTER_NONE = ClusterType.None


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy with deadline-aware spot usage."""

    NAME = "cant_be_late_multi_region_v1"

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

        # Internal progress tracking (avoid O(n^2) summations).
        self._last_done_segments = len(getattr(self, "task_done_time", []))
        self._done_so_far = sum(self.task_done_time) if self.task_done_time else 0.0

        # Deadline / safety parameters (in seconds).
        td = float(self.task_duration)
        ro = float(self.restart_overhead)

        # Safety slack: keep at least 20% of task_duration or 10x restart_overhead.
        base_slack = 0.2 * td
        min_slack = 10.0 * ro
        self.safety_slack = max(base_slack, min_slack)

        # While slack is very high, we are willing to wait (NONE) when spot is down.
        self.wait_slack_multiplier = 2.0

        # Once we decide to guarantee completion with ON_DEMAND, never go back to spot.
        self.commit_to_ondemand = False

        return self

    def _update_progress(self) -> None:
        """Incrementally track total completed work."""
        n = len(self.task_done_time)
        if n > self._last_done_segments:
            new_segments = self.task_done_time[self._last_done_segments :]
            if new_segments:
                self._done_so_far += sum(new_segments)
            self._last_done_segments = n

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update internal progress tracking.
        self._update_progress()

        # Remaining time and work (seconds).
        elapsed = float(self.env.elapsed_seconds)
        remaining_time = float(self.deadline) - elapsed
        if remaining_time <= 0.0:
            # Past deadline: nothing meaningful to do; avoid extra cost.
            return CLUSTER_NONE

        rem_work = float(self.task_duration) - self._done_so_far
        if rem_work <= 0.0:
            # Job already done.
            return CLUSTER_NONE

        ro = float(self.restart_overhead)

        # Slack if we were to switch to ON_DEMAND and run to completion.
        slack_time = remaining_time - (rem_work + ro)

        # If not yet committed, decide whether it's time to lock into ON_DEMAND.
        if not self.commit_to_ondemand:
            if slack_time <= self.safety_slack:
                self.commit_to_ondemand = True

        # Once committed, always use ON_DEMAND to guarantee completion.
        if self.commit_to_ondemand:
            return ClusterType.ON_DEMAND

        # If we're already behind (negative slack), immediately run ON_DEMAND.
        if slack_time <= 0.0:
            return ClusterType.ON_DEMAND

        # Pre-commit phase.
        if has_spot:
            # Spot available and we're comfortably before the commit threshold.
            return ClusterType.SPOT

        # Spot not available in current region.
        # If we have a lot of slack, simply wait to save cost.
        wait_threshold = self.wait_slack_multiplier * self.safety_slack
        if slack_time > wait_threshold:
            return CLUSTER_NONE

        # Slack is moderate; make progress using ON_DEMAND.
        return ClusterType.ON_DEMAND
