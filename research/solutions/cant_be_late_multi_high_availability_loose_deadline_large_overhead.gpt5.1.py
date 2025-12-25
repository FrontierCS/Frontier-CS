import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy focused on cost minimization with a safe on-demand fallback."""

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

        # Internal state initialization
        self._cached_progress = 0.0
        self._last_task_done_len = 0
        self.committed_to_ondemand = False

        # Derive parameters (seconds)
        # These attributes should be set by MultiRegionStrategy.__init__,
        # but we fall back to spec values (in hours) if needed.
        try:
            task_duration = float(self.task_duration)
        except Exception:
            task_duration = float(config["duration"]) * 3600.0

        try:
            restart_overhead = float(self.restart_overhead)
        except Exception:
            restart_overhead = float(config["overhead"]) * 3600.0

        try:
            deadline = float(self.deadline)
        except Exception:
            deadline = float(config["deadline"]) * 3600.0

        try:
            gap = float(self.env.gap_seconds)
        except Exception:
            gap = 0.0

        slack = max(0.0, deadline - task_duration)

        # Commit margin: how much slack we keep when falling back to on-demand
        # - Large enough to tolerate worst-case degradation between steps
        # - Small enough to avoid switching to on-demand too early
        base_margin = 4.0 * (gap + restart_overhead)  # tolerate several bad steps
        frac_margin = 0.25 * task_duration  # at most 1/4 of job time
        self.commit_margin_seconds = min(base_margin, frac_margin, slack)

        # Ensure non-negative margin
        if self.commit_margin_seconds < 0.0:
            self.commit_margin_seconds = 0.0

        return self

    def _update_cached_progress(self) -> None:
        """Incrementally track total completed work time."""
        current_len = len(self.task_done_time)
        if current_len > self._last_task_done_len:
            # Sum only new segments to keep overall complexity O(N)
            new_sum = 0.0
            for i in range(self._last_task_done_len, current_len):
                new_sum += self.task_done_time[i]
            self._cached_progress += new_sum
            self._last_task_done_len = current_len

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update cached work progress
        self._update_cached_progress()

        # Remaining work (seconds)
        remaining_work = self.task_duration - self._cached_progress
        if remaining_work <= 0.0:
            # Task completed; no need to run anything further.
            self.committed_to_ondemand = False
            return ClusterType.NONE

        # Time left until deadline
        available_time = self.deadline - self.env.elapsed_seconds

        # If we're already past deadline (should be rare), just use on-demand
        if available_time <= 0.0:
            return ClusterType.ON_DEMAND

        # Decide whether to permanently fall back to on-demand
        if not self.committed_to_ondemand:
            # Overhead incurred if we switch to on-demand now
            if last_cluster_type == ClusterType.ON_DEMAND:
                overhead_if_commit = 0.0
            else:
                overhead_if_commit = self.restart_overhead

            required_if_commit = remaining_work + overhead_if_commit
            slack_if_commit = available_time - required_if_commit

            # Commit to on-demand once slack becomes small enough.
            # This guarantees completion before deadline under our margin assumptions.
            if slack_if_commit <= self.commit_margin_seconds:
                self.committed_to_ondemand = True

        # After committing, always use on-demand (never switch back).
        if self.committed_to_ondemand:
            return ClusterType.ON_DEMAND

        # Pre-commit: prefer spot; if unavailable, pause (NONE) to avoid restart overheads.
        if has_spot:
            return ClusterType.SPOT

        # Spot unavailable and far from commit: it's safe to idle and rely on future spot/OD fallback.
        return ClusterType.NONE