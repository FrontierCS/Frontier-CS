import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy implementation."""

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

        # Extract scalar versions of key parameters (in seconds).
        td = getattr(self, "task_duration", None)
        if isinstance(td, (list, tuple)):
            self._task_duration_sec = float(td[0])
        else:
            self._task_duration_sec = float(td)

        ro = getattr(self, "restart_overhead", None)
        if isinstance(ro, (list, tuple)):
            self._restart_overhead_sec = float(ro[0])
        else:
            self._restart_overhead_sec = float(ro)

        self._deadline_sec = float(getattr(self, "deadline", 0.0))

        # Precompute initial slack (effective time for useful work).
        self._initial_slack_sec = max(
            self._deadline_sec - self._task_duration_sec, 0.0
        )

        # Cumulative work done cache to avoid summing list every step.
        self._done_work_sec = 0.0
        self._last_done_len = 0

        # Strategy control flags and thresholds.
        self._committed_to_on_demand = False
        self._always_on_demand = False
        self._slack_idle_threshold = 0.0
        self._slack_spot_threshold = 0.0

        over = self._restart_overhead_sec
        slack_init = self._initial_slack_sec

        # If almost no slack or no overhead concept, just use On-Demand.
        if over <= 0.0 or slack_init <= 3.0 * over:
            self._always_on_demand = True
        else:
            # Compute conservative thresholds for when we stop idling / using Spot.
            # We guarantee at least 'over' time of slack reserved to pay one restart.
            # Idle threshold: when slack <= this, we must stop idling and start On-Demand.
            # Spot threshold: when slack <= this, we stop using Spot and commit to On-Demand.
            reserve_min = over
            # Use up to ~2% of initial slack or at least 2*over for idling, but leave reserve.
            idle_candidate = max(2.0 * over, 0.02 * slack_init)
            max_allowed = max(slack_init - reserve_min, reserve_min)
            B_idle = min(idle_candidate, max_allowed)
            if B_idle < reserve_min:
                B_idle = reserve_min

            # Require at least an extra 'over' margin when still using Spot.
            B_spot = B_idle + over
            max_allowed_spot = max(slack_init - reserve_min, B_idle)
            if B_spot > max_allowed_spot:
                B_spot = max_allowed_spot
            if B_spot < B_idle:
                B_spot = B_idle

            self._slack_idle_threshold = B_idle
            self._slack_spot_threshold = B_spot

        return self

    def _update_done_work_cache(self) -> None:
        """Incrementally update cached total work done."""
        td_list = self.task_done_time
        n = len(td_list)
        if n > self._last_done_len:
            # Sum only the new segments.
            new_sum = 0.0
            for v in td_list[self._last_done_len : n]:
                new_sum += v
            self._done_work_sec += new_sum
            self._last_done_len = n

    def _compute_slack(self) -> float:
        """
        Compute effective slack: (deadline - elapsed - pending_overhead) - remaining_work.
        """
        self._update_done_work_cache()

        remaining_work = max(self._task_duration_sec - self._done_work_sec, 0.0)
        remaining_time = max(self._deadline_sec - self.env.elapsed_seconds, 0.0)
        pending_overhead = float(getattr(self, "remaining_restart_overhead", 0.0))

        effective_remaining_time = max(remaining_time - pending_overhead, 0.0)
        slack = effective_remaining_time - remaining_work
        return slack

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If task is already done, don't run anything.
        self._update_done_work_cache()
        if self._done_work_sec >= self._task_duration_sec:
            return ClusterType.NONE

        # If configured to always use on-demand, do so.
        if self._always_on_demand or self._committed_to_on_demand:
            return ClusterType.ON_DEMAND

        slack = self._compute_slack()
        over = self._restart_overhead_sec

        # If slack is very small, immediately commit to On-Demand.
        if slack <= over:
            self._committed_to_on_demand = True
            return ClusterType.ON_DEMAND

        # When Spot is unavailable.
        if not has_spot:
            # If we are close to consuming reserved slack, start On-Demand.
            if slack <= self._slack_idle_threshold:
                self._committed_to_on_demand = True
                return ClusterType.ON_DEMAND
            # Otherwise, wait (NONE) to save cost and consume slack.
            return ClusterType.NONE

        # Spot is available.
        # If slack is below the Spot threshold, commit to On-Demand.
        if slack <= self._slack_spot_threshold:
            self._committed_to_on_demand = True
            return ClusterType.ON_DEMAND

        # Otherwise, safely use Spot.
        return ClusterType.SPOT