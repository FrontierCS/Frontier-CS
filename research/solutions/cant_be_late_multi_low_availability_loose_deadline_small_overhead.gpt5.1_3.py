import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy focusing on spot usage with hard deadline guarantee."""

    NAME = "cbm_multi_region_spot_od"

    def solve(self, spec_path: str) -> "Solution":
        """Initialize the solution from spec_path config."""
        with open(spec_path) as f:
            config = json.load(f)

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)

        # Helper to safely get scalar from possible list/tuple.
        def _scalar(v):
            if isinstance(v, (list, tuple)):
                return float(v[0])
            return float(v)

        # Cache key parameters in seconds.
        self._task_total_seconds = _scalar(self.task_duration)
        self._restart_seconds = _scalar(self.restart_overhead)
        self._deadline_seconds = _scalar(self.deadline)
        self._gap_seconds = float(getattr(self.env, "gap_seconds", 0.0))

        # Slack threshold for switching permanently to on-demand.
        # Chosen conservatively to absorb at most one bad step (idle or fully preempted).
        base_threshold = self._gap_seconds + 4.0 * self._restart_seconds
        # Ensure at least restart overhead margin.
        self._slack_threshold = max(base_threshold, self._restart_seconds)

        # Once this flag is set, we will always use on-demand.
        self._in_on_demand_mode = False

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """Decide next action based on current state."""
        # Current progress and remaining work.
        progress_done = float(sum(self.task_done_time))
        remaining_work = self._task_total_seconds - progress_done

        # If already finished, don't run more.
        if remaining_work <= 0.0:
            return ClusterType.NONE

        # Remaining time until deadline.
        elapsed = float(self.env.elapsed_seconds)
        remaining_time = self._deadline_seconds - elapsed

        # If somehow past deadline, still try to run on-demand to minimize lateness.
        if remaining_time <= 0.0:
            return ClusterType.ON_DEMAND

        # Slack = extra time beyond what is needed at full-speed on-demand.
        slack = remaining_time - remaining_work

        # Decide if we must switch to on-demand permanently.
        if not self._in_on_demand_mode:
            if slack <= self._slack_threshold:
                self._in_on_demand_mode = True

        if self._in_on_demand_mode:
            # From now on, always on-demand to guarantee completion.
            return ClusterType.ON_DEMAND

        # Spot-preferred mode: use spot when available, otherwise wait (NONE).
        if has_spot:
            return ClusterType.SPOT

        # Spot unavailable and we still have ample slack: wait to avoid on-demand cost.
        return ClusterType.NONE