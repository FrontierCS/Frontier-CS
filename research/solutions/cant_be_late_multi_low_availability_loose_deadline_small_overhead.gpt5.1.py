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

        # Extract core parameters (seconds), handling both scalar and list forms.
        try:
            if isinstance(self.deadline, (list, tuple)):
                deadline_seconds = float(self.deadline[0])
            else:
                deadline_seconds = float(self.deadline)
        except AttributeError:
            deadline_seconds = float(getattr(self, "deadline", 0.0))

        try:
            if isinstance(self.task_duration, (list, tuple)):
                task_duration_seconds = float(self.task_duration[0])
            else:
                task_duration_seconds = float(self.task_duration)
        except AttributeError:
            task_duration_seconds = float(getattr(self, "task_duration", 0.0))

        try:
            if isinstance(self.restart_overhead, (list, tuple)):
                restart_overhead_seconds = float(self.restart_overhead[0])
            else:
                restart_overhead_seconds = float(self.restart_overhead)
        except AttributeError:
            restart_overhead_seconds = float(getattr(self, "restart_overhead", 0.0))

        self._deadline_sec = deadline_seconds
        self._task_duration_sec = task_duration_seconds
        self._restart_overhead_sec = restart_overhead_seconds

        # Scheduling parameters based on slack.
        slack_total = max(0.0, deadline_seconds - task_duration_seconds)

        # Safety buffer before fully committing to on-demand.
        # At least twice the restart overhead, and at least 10% of initial slack.
        self._safety_buffer_seconds = max(
            2.0 * restart_overhead_seconds,
            0.1 * slack_total,
        )

        # If slack exceeds this threshold, we're comfortable idling when spot is down.
        self._wait_slack_threshold = 0.5 * slack_total

        # Incremental tracking of completed work to avoid O(n) summations.
        self._total_done_time = 0.0
        self._last_done_index = 0

        # Control flags and counters.
        self._forced_on_demand = False
        self._step_counter = 0

        return self

    def _update_done_time_cache(self) -> None:
        """Incrementally accumulate completed work time."""
        td = self.task_done_time
        last = self._last_done_index
        n = len(td)
        if n > last:
            total = self._total_done_time
            for i in range(last, n):
                total += td[i]
            self._total_done_time = total
            self._last_done_index = n

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.

        Returns: ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        self._step_counter += 1

        # Update cached total amount of work done.
        self._update_done_time_cache()
        remaining_work = self._task_duration_sec - self._total_done_time
        if remaining_work <= 0.0:
            # Task already completed.
            return ClusterType.NONE

        # Time information.
        elapsed = float(self.env.elapsed_seconds)
        remaining_time = self._deadline_sec - elapsed

        if remaining_time <= 0.0:
            # Out of time; best effort is to use on-demand.
            return ClusterType.ON_DEMAND

        # Check if we must commit to on-demand to safely meet deadline.
        if (not self._forced_on_demand) and remaining_time <= remaining_work + self._safety_buffer_seconds:
            self._forced_on_demand = True

        if self._forced_on_demand:
            return ClusterType.ON_DEMAND

        # Opportunistic phase: prefer Spot when available.
        if has_spot:
            return ClusterType.SPOT

        # Spot not available: decide between waiting (NONE) and using On-Demand.
        slack = remaining_time - remaining_work

        # If we still have plenty of slack, we can afford to wait for Spot.
        if slack > self._wait_slack_threshold:
            return ClusterType.NONE

        # Slack is shrinking but not yet critical: use On-Demand to keep progress steady.
        return ClusterType.ON_DEMAND