import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy."""

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

        # Internal state for efficient progress tracking
        self._done_time_sum = 0.0
        self._done_time_len = 0
        self._force_on_demand = False
        return self

    def _get_scalar(self, value):
        if isinstance(value, (list, tuple)):
            return float(value[0])
        return float(value)

    def _update_done_time_sum(self):
        """Incrementally update cached sum of task_done_time."""
        segs = self.task_done_time
        n = len(segs)
        if n > self._done_time_len:
            total = self._done_time_sum
            for i in range(self._done_time_len, n):
                total += segs[i]
            self._done_time_sum = total
            self._done_time_len = n

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update cached progress
        self._update_done_time_sum()

        task_duration = self._get_scalar(self.task_duration)
        restart_overhead = self._get_scalar(self.restart_overhead)
        # deadline is already scalar in the environment
        deadline = float(self.deadline)

        # Remaining work in seconds
        remaining_work = max(task_duration - self._done_time_sum, 0.0)

        # If task is already done, no need to run more
        if remaining_work <= 0.0:
            return ClusterType.NONE

        elapsed = float(self.env.elapsed_seconds)
        time_left = deadline - elapsed

        # If we've already passed the deadline, just use on-demand (nothing else to do)
        if time_left <= 0.0:
            return ClusterType.ON_DEMAND

        # Pending restart overhead tracked by the environment, if available
        pending_overhead = float(getattr(self, "remaining_restart_overhead", 0.0))

        # Time needed if we switch to ON_DEMAND now and stay there
        if last_cluster_type is ClusterType.ON_DEMAND:
            # No new overhead introduced; just pay whatever is already pending
            time_needed_od = remaining_work + pending_overhead
        else:
            # Switching to ON_DEMAND will replace pending_overhead with restart_overhead
            effective_overhead = max(restart_overhead, pending_overhead)
            time_needed_od = remaining_work + effective_overhead

        gap = float(self.env.gap_seconds)

        # Drop-dead condition: if taking one more non-ON_DEMAND step would make it
        # impossible to finish with ON_DEMAND alone, commit to ON_DEMAND now.
        if (not self._force_on_demand) and (time_left <= time_needed_od + gap):
            self._force_on_demand = True

        # Once we force ON_DEMAND, never go back to SPOT to avoid extra risk.
        if self._force_on_demand:
            return ClusterType.ON_DEMAND

        # Opportunistic phase (not yet forced to on-demand)

        # Prefer SPOT when available in the safe window
        if has_spot:
            return ClusterType.SPOT

        # Spot is unavailable: decide between ON_DEMAND and NONE based on slack
        # Slack ignoring future overheads (conservative but simple)
        slack = time_left - remaining_work

        # If slack is small, we should use ON_DEMAND to keep schedule safe.
        # Threshold: allow idling while we have several steps of slack.
        slack_threshold = 4.0 * gap
        if slack_threshold < 2.0 * restart_overhead:
            slack_threshold = 2.0 * restart_overhead

        if slack <= slack_threshold:
            # Getting tight on slack: use ON_DEMAND to make progress
            return ClusterType.ON_DEMAND

        # Plenty of slack and no spot: wait (NONE) to save cost
        return ClusterType.NONE
