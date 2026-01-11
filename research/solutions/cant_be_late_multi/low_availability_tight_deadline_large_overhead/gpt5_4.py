import json
from argparse import Namespace
from typing import Optional

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "deadline_guard_v2"

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

        # Internal state
        self._od_mode: bool = False
        self._od_lock_until: float = 0.0
        self._outage_wait_start: Optional[float] = None
        self._last_elapsed: Optional[float] = None

        return self

    # Helpers
    def _reset_state(self):
        self._od_mode = False
        self._od_lock_until = 0.0
        self._outage_wait_start = None
        self._last_elapsed = self.env.elapsed_seconds

    def _get_params(self):
        # Dynamic parameters based on environment
        gap = getattr(self.env, "gap_seconds", 3600.0)
        ro = float(getattr(self, "restart_overhead", 0.0))
        # OD commit threshold: when slack <= threshold, switch to OD immediately
        od_threshold = max(2.0 * gap, 1800.0, 2.0 * ro)
        # OD lock duration: min amount of time to remain on OD once committed
        od_min_run = max(2.0 * gap, 1800.0)
        # Slack margin to consider switching back from OD to SPOT if available
        release_threshold = od_threshold + max(3.0 * gap, 3600.0)
        # Waiting policy when SPOT unavailable and not in OD mode
        abs_wait_cap = 7200.0  # cap waiting per outage at 2h
        slack_wait_fraction = 0.5  # can wait up to 50% of current slack (bounded by abs_wait_cap)
        return od_threshold, od_min_run, release_threshold, abs_wait_cap, slack_wait_fraction

    def _compute_slack(self):
        elapsed = float(self.env.elapsed_seconds)
        deadline = float(self.deadline)
        work_done = float(sum(self.task_done_time)) if self.task_done_time else 0.0
        remaining_work = max(0.0, float(self.task_duration) - work_done)
        ro = float(self.restart_overhead)
        time_left = deadline - elapsed
        slack = time_left - (remaining_work + ro)
        return slack, remaining_work, time_left

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Detect episode reset
        if self._last_elapsed is None or self.env.elapsed_seconds < (self._last_elapsed or 0.0) or self.env.elapsed_seconds == 0.0:
            self._reset_state()
        else:
            self._last_elapsed = self.env.elapsed_seconds

        # If already finished (defensive)
        work_done = float(sum(self.task_done_time)) if self.task_done_time else 0.0
        if work_done >= float(self.task_duration):
            return ClusterType.NONE

        # Compute current slack
        slack, remaining_work, time_left = self._compute_slack()
        # If we are basically out of time, run OD
        if time_left <= 0.0:
            self._od_mode = True
            return ClusterType.ON_DEMAND

        od_threshold, od_min_run, release_threshold, abs_wait_cap, slack_wait_fraction = self._get_params()

        # OD mode handling
        if self._od_mode:
            # Consider switching back to spot if:
            # - OD lock period passed
            # - Slack is comfortably large
            # - Spot is available
            if has_spot and self.env.elapsed_seconds >= self._od_lock_until and slack >= release_threshold:
                self._od_mode = False
                self._outage_wait_start = None
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND

        # Not in OD mode
        # If slack is low, use OD proactively (even if spot is currently available) to guarantee completion
        if slack <= od_threshold:
            self._od_mode = True
            self._od_lock_until = self.env.elapsed_seconds + od_min_run
            self._outage_wait_start = None
            return ClusterType.ON_DEMAND

        # Prefer SPOT when available and slack is healthy
        if has_spot:
            self._outage_wait_start = None
            return ClusterType.SPOT

        # SPOT unavailable and not in OD mode: decide to wait (NONE) or switch to OD based on slack and wait budget
        if self._outage_wait_start is None:
            self._outage_wait_start = self.env.elapsed_seconds

        waited = max(0.0, self.env.elapsed_seconds - self._outage_wait_start)
        # Allowed wait: at most half the current slack (so we can still switch to OD),
        # additionally bounded by abs_wait_cap, and ensuring we keep od_threshold buffer
        wait_budget = max(0.0, min(abs_wait_cap, slack * slack_wait_fraction, max(0.0, slack - od_threshold)))

        if waited < wait_budget:
            return ClusterType.NONE

        # Exceeded wait budget: commit to OD
        self._od_mode = True
        self._od_lock_until = self.env.elapsed_seconds + od_min_run
        self._outage_wait_start = None
        return ClusterType.ON_DEMAND