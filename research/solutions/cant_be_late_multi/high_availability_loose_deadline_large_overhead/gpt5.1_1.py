import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Deadline-safe, cost-aware multi-region scheduling strategy."""

    NAME = "deadline_safe_threshold"

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the solution from spec_path config.

        The spec file contains:
        - deadline: deadline in hours
        - duration: task duration in hours
        - overhead: restart overhead in hours
        - trace_files: list of trace file paths (one per region)  # unused here
        """
        with open(spec_path, "r") as f:
            config = json.load(f)

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)

        # Custom state initialization
        self._initialized = False
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.

        Returns: ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        # Lazy initialization (env not available in __init__)
        if not getattr(self, "_initialized", False):
            self._initialized = True
            self._last_task_done_idx = 0
            self._done_work = 0.0
            self._committed = False

        # Update accumulated work using any new completed segments.
        segs = self.task_done_time
        last_idx = self._last_task_done_idx
        if last_idx < len(segs):
            new_work = 0.0
            for s in segs[last_idx:]:
                new_work += s
            self._done_work += new_work
            self._last_task_done_idx = len(segs)

        # If task already completed, do not run any more clusters.
        if self._done_work >= self.task_duration:
            return ClusterType.NONE

        remaining_work = self.task_duration - self._done_work
        time_left = self.deadline - self.env.elapsed_seconds

        # If we're past the deadline (shouldn't usually happen), still try best effort.
        if time_left <= 0:
            return ClusterType.ON_DEMAND

        dt = self.env.gap_seconds
        r = self.restart_overhead

        # Small safety buffer to guard against discretization / rounding.
        safety_buffer = dt

        if not self._committed:
            # Slack between available time and worst-case required time
            # to finish on pure on-demand from *after* this step, assuming
            # this step could yield zero useful work.
            # We require that even after "wasting" one full step, we can still
            # finish with on-demand only.
            slack = time_left - (remaining_work + r + safety_buffer)

            # If after one potentially wasted step we still have enough time,
            # it's safe to keep relying on spot / waiting.
            if slack >= dt:
                if has_spot:
                    return ClusterType.SPOT
                # No spot and plenty of slack: wait; no cost, preserves safety.
                return ClusterType.NONE

            # Not enough slack to risk another potentially wasted step:
            # from now on, commit to on-demand only.
            self._committed = True

        # Committed phase: always use on-demand to guarantee completion.
        return ClusterType.ON_DEMAND