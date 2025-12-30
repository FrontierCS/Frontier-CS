import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy with slack-based Spot/On-Demand control."""

    NAME = "slack_based_multi_region_strategy"

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

        # Caches for efficient computation of work done
        self._cached_done_work = 0.0
        self._cached_segments = 0

        # Fallback state: once True, always use On-Demand until job completion
        self._fallback_committed = False

        # Precompute slack-based parameters in seconds
        try:
            total_slack = max(self.deadline - self.task_duration - self.restart_overhead, 0.0)
        except AttributeError:
            # In case attributes are not set as expected; be conservative
            self._fallback_committed = True
            self._idle_slack_threshold = 0.0
            return self

        if total_slack <= 0.0:
            # No slack: we must rely on On-Demand from the start to avoid deadline miss
            self._fallback_committed = True
            self._idle_slack_threshold = 0.0
        else:
            # Allow idling when slack is large, but cap the idle threshold
            # to avoid over-waiting for very lax deadlines.
            # Use 60% of total slack, at most 6 hours.
            self._idle_slack_threshold = min(total_slack * 0.6, 6.0 * 3600.0)

        return self

    def _effective_done_work(self) -> float:
        """Incrementally compute total work done from task_done_time segments."""
        segments = self.task_done_time
        n = len(segments)
        if n != self._cached_segments:
            # Sum only the new segments since last call
            total_new = 0.0
            for i in range(self._cached_segments, n):
                total_new += segments[i]
            self._cached_done_work += total_new
            self._cached_segments = n
        return self._cached_done_work

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        env = self.env

        # Compute work done so far
        work_done = self._effective_done_work()
        remaining_work = self.task_duration - work_done

        # If task is completed, do nothing to avoid extra cost
        if remaining_work <= 0.0:
            self._fallback_committed = True
            return ClusterType.NONE

        # Time left until deadline
        time_left = self.deadline - env.elapsed_seconds
        if time_left <= 0.0:
            # Already past deadline; nothing better than use On-Demand
            self._fallback_committed = True
            return ClusterType.ON_DEMAND

        gap = env.gap_seconds

        # Decide whether to commit to On-Demand fallback
        if not self._fallback_committed:
            # Slack: time we can afford to spend with no further progress
            # before we must switch to On-Demand and still finish in time.
            slack = time_left - (remaining_work + self.restart_overhead)

            if slack <= 0.0:
                # No slack left: must commit now
                self._fallback_committed = True
            else:
                # Minimum slack needed to allow one more risky step (Spot/None)
                # We use an epsilon to guard against floating-point issues.
                min_slack_for_risky_step = gap + 1e-6
                if slack < min_slack_for_risky_step:
                    # Not enough slack for another risky step
                    self._fallback_committed = True

        # If committed, always use On-Demand until completion
        if self._fallback_committed:
            return ClusterType.ON_DEMAND

        # Recompute slack for idling/On-Demand choice (env state unchanged)
        slack = time_left - (remaining_work + self.restart_overhead)

        # Prefer Spot while available and we still have slack to buffer risks
        if has_spot:
            return ClusterType.SPOT

        # No Spot available: decide between idling and switching to On-Demand
        if slack > self._idle_slack_threshold:
            # Slack is large: we can afford to wait for cheaper Spot
            return ClusterType.NONE

        # Slack is not large anymore: commit to On-Demand from now on
        self._fallback_committed = True
        return ClusterType.ON_DEMAND