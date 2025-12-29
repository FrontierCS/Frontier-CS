import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Safe cost-aware multi-region scheduling strategy."""

    NAME = "safe_spot_ondemand_hybrid"

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
        self._done_work_sum = 0.0
        self._task_segments_len = 0
        self._committed_ondemand = False

        # Precompute a conservative commit margin (seconds).
        # Ensure it's at least ~2 steps plus two restart overheads.
        gap = float(getattr(self.env, "gap_seconds", 3600.0))
        restart_overhead = float(self.restart_overhead)
        self._commit_margin = max(2.0 * gap, 2.0 * restart_overhead)

        return self

    def _update_done_work_sum(self) -> None:
        """Incrementally track total completed work to avoid O(N^2) summations."""
        segments = self.task_done_time
        current_len = len(segments)
        if current_len > self._task_segments_len:
            # Add any new segments since last step.
            for i in range(self._task_segments_len, current_len):
                self._done_work_sum += float(segments[i])
            self._task_segments_len = current_len

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update cached total work done.
        self._update_done_work_sum()

        # Remaining work in seconds.
        remaining_work = float(self.task_duration) - self._done_work_sum
        if remaining_work <= 0.0:
            # Task logically complete; no need to run any more clusters.
            self._committed_ondemand = True
            return ClusterType.NONE

        # If we have already committed to on-demand, always stay on it.
        if self._committed_ondemand:
            return ClusterType.ON_DEMAND

        # Compute slack if we were to switch to pure on-demand now.
        now = float(self.env.elapsed_seconds)
        deadline = float(self.deadline)
        restart_overhead = float(self.restart_overhead)

        # Worst-case additional time to finish if we use only on-demand from now:
        # restart_overhead (once) + remaining_work
        finish_time_if_od_now = now + restart_overhead + remaining_work
        slack_if_od = deadline - finish_time_if_od_now

        # If slack is small, commit to on-demand to guarantee deadline.
        # We commit as soon as slack_if_od <= commit_margin to ensure we don't
        # cross into negative slack between steps.
        if slack_if_od <= self._commit_margin:
            self._committed_ondemand = True
            return ClusterType.ON_DEMAND

        # Pre-commit phase: prefer Spot when available, otherwise pause.
        if has_spot:
            return ClusterType.SPOT

        # Spot unavailable and we still have comfortable slack: wait to save cost.
        return ClusterType.NONE