import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy that prioritizes Spot while guaranteeing deadline."""

    NAME = "cant_be_late_v1"

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

        # Internal state for efficient tracking of work done
        self._work_done = 0.0
        self._segments_seen = 0
        self._commit_to_on_demand = False

        return self

    def _update_work_done(self) -> None:
        """Incrementally update total work done from task_done_time segments."""
        segments = self.task_done_time
        n = len(segments)
        if n > self._segments_seen:
            # Sum only the new segments to keep amortized O(1) per step.
            self._work_done += sum(segments[self._segments_seen:n])
            self._segments_seen = n

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.

        Returns: ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        # Update cached progress
        self._update_work_done()

        remaining_work = max(self.task_duration - self._work_done, 0.0)
        if remaining_work <= 0.0:
            # Task already completed; avoid incurring any further cost.
            return ClusterType.NONE

        current_time = self.env.elapsed_seconds
        margin = self.deadline - current_time

        # If we've already passed the deadline (should be rare), further work is pointless for scoring.
        if margin <= 0.0:
            return ClusterType.NONE

        # "Slack" is the time left beyond what is needed (ignoring future restart overheads).
        slack = margin - remaining_work

        # Determine a safety buffer that accounts for discretization (gap) and some extra cushion.
        gap = getattr(self.env, "gap_seconds", 1.0)
        base_buffer = 600.0  # 10 minutes base safety margin
        dynamic_buffer = max(base_buffer, 2.0 * gap)

        # To safely complete on On-Demand with discrete steps, we need at least:
        # restart_overhead + gap of extra slack at commit time.
        threshold_slack = self.restart_overhead + dynamic_buffer

        # If we've already committed to On-Demand, keep using it to avoid extra restarts.
        if self._commit_to_on_demand:
            return ClusterType.ON_DEMAND

        # Check whether it's time to commit to On-Demand to guarantee completion.
        if slack <= threshold_slack:
            self._commit_to_on_demand = True
            return ClusterType.ON_DEMAND

        # Before committing to On-Demand, always prefer Spot if available.
        if has_spot:
            return ClusterType.SPOT

        # Spot unavailable and we still have enough slack:
        # wait (NONE) to preserve budget, relying on future Spot or the eventual On-Demand fallback.
        return ClusterType.NONE