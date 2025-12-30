import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Safe slack-based multi-region scheduling strategy."""

    NAME = "safe_spot_slack_v1"

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

        # Custom state for our strategy
        self._internal_initialized = False
        self._force_on_demand = False

        # Track cumulative work without recomputing sum() every step
        self._last_progress_index = 0
        self._total_done_work = 0.0

        return self

    def _initialize_internal(self):
        """Lazily initialize internal parameters that depend on the env."""
        if self._internal_initialized:
            return
        gap = getattr(self.env, "gap_seconds", 0.0) or 0.0

        # Commit to on-demand when remaining slack falls below this.
        # This guarantees enough time to pay one restart overhead and
        # finish the remaining work on on-demand (no preemptions).
        self._commit_slack = self.restart_overhead + gap

        self._gap_seconds = gap
        self._internal_initialized = True

    def _update_progress(self):
        """Incrementally track total completed work to avoid O(n) per step."""
        segments = self.task_done_time
        idx = self._last_progress_index
        if segments is None:
            return
        n = len(segments)
        if n > idx:
            # Sum only newly added segments
            self._total_done_work += sum(segments[idx:n])
            self._last_progress_index = n

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._initialize_internal()
        self._update_progress()

        # Remaining work in seconds
        remaining_work = self.task_duration - self._total_done_work
        if remaining_work <= 0:
            # Job already done; refuse to run more
            return ClusterType.NONE

        elapsed = self.env.elapsed_seconds
        time_left = self.deadline - elapsed

        if time_left <= 0:
            # Already past deadline; nothing can help but return ON_DEMAND
            # (environment will handle penalty).
            return ClusterType.ON_DEMAND

        slack = time_left - remaining_work

        # Once we decide it's safer to stay on on-demand, never go back.
        if self._force_on_demand or slack <= self._commit_slack:
            self._force_on_demand = True
            return ClusterType.ON_DEMAND

        # We are in the "safe" region with enough slack.
        # Prefer Spot when available (cheapest); otherwise wait (NONE) to
        # avoid expensive on-demand while we still have slack.
        if has_spot:
            return ClusterType.SPOT

        # Spot not available and we still have plenty of slack: wait.
        return ClusterType.NONE