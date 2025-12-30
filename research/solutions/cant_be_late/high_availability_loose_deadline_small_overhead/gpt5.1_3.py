import math
from typing import Any

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args: Any = None):
        super().__init__(args)
        self.args = args
        self._initialized = False
        self.total_slack = 0.0
        self.base_idle_fraction = 0.3
        self.nospot_fraction = 0.1
        self.base_idle_threshold = 0.0
        self.slack_no_spot_threshold = 0.0
        self.time_observed = 0.0
        self.time_spot_available = 0.0

    def solve(self, spec_path: str) -> "Solution":
        # Optional: load configuration from spec_path if needed.
        return self

    def _initialize_if_needed(self):
        if self._initialized:
            return
        # Total slack is how much wall-clock time we can afford to lose beyond
        # the pure compute time if we ran continuously.
        try:
            deadline = float(self.deadline)
        except Exception:
            deadline = 0.0
        try:
            task_duration = float(self.task_duration)
        except Exception:
            task_duration = 0.0
        self.total_slack = max(deadline - task_duration, 0.0)

        # Fractions of total slack used for heuristic thresholds.
        self.base_idle_fraction = 0.3   # portion of slack we are comfortable spending before avoiding idling
        self.nospot_fraction = 0.1      # below this remaining slack, avoid spot altogether

        self.base_idle_threshold = self.total_slack * self.base_idle_fraction
        self.slack_no_spot_threshold = self.total_slack * self.nospot_fraction

        self.time_observed = 0.0
        self.time_spot_available = 0.0

        self._initialized = True

    def _compute_progress(self) -> float:
        total = 0.0
        segments = getattr(self, "task_done_time", []) or []
        for seg in segments:
            # Case 1: duration given directly as a number.
            if isinstance(seg, (int, float)):
                total += float(seg)
                continue
            # Case 2: treat as (start, end).
            try:
                start, end = seg  # type: ignore
                total += float(end) - float(start)
                continue
            except Exception:
                pass
            # Case 3: object with .duration attribute.
            dur = getattr(seg, "duration", None)
            if isinstance(dur, (int, float)):
                total += float(dur)
        return max(total, 0.0)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._initialize_if_needed()

        dt = getattr(self.env, "gap_seconds", 0.0) or 0.0
        self.time_observed += dt
        if has_spot:
            self.time_spot_available += dt

        progress = self._compute_progress()
        try:
            task_duration = float(self.task_duration)
        except Exception:
            task_duration = 0.0
        remaining_work = max(task_duration - progress, 0.0)

        # If work is completed, do nothing.
        if remaining_work <= 0.0:
            return ClusterType.NONE

        now = getattr(self.env, "elapsed_seconds", 0.0) or 0.0
        try:
            deadline = float(self.deadline)
        except Exception:
            deadline = now
        remaining_time = max(deadline - now, 0.0)

        slack_remaining = remaining_time - remaining_work

        try:
            restart_overhead = float(self.restart_overhead)
        except Exception:
            restart_overhead = 0.0

        # Safety window: minimal time buffer to cover restart overhead and discretization.
        safety_window = max(restart_overhead, dt * 2.0)

        # If there is effectively no slack for restarts, always use on-demand.
        if self.total_slack <= restart_overhead * 2.0:
            return ClusterType.ON_DEMAND

        # If we already have negative slack or almost no slack left, we must
        # run on-demand to try to salvage the schedule.
        if slack_remaining <= 0.0 or remaining_time <= remaining_work + safety_window:
            return ClusterType.ON_DEMAND

        # Base idle threshold before adaptation.
        idle_threshold = self.base_idle_threshold

        # Adapt idle threshold based on observed spot availability, but only
        # after some minimum observation time to avoid noise.
        if self.time_observed > 0.0:
            min_obs_time = min(6 * 3600.0, 0.1 * max(deadline, 1.0))
            if self.time_observed >= max(min_obs_time, 1.0):
                avail_est = self.time_spot_available / self.time_observed
                # If spot availability is poor, become more conservative
                # (increase idle threshold). If availability is very good,
                # we can afford to be slightly more aggressive (lower threshold).
                if avail_est < 0.5:
                    idle_threshold *= 1.3
                elif avail_est > 0.7:
                    idle_threshold *= 0.7

        # Clamp idle threshold to reasonable bounds relative to total slack.
        if self.total_slack > 0.0:
            lower_bound = self.total_slack * 0.1
            upper_bound = self.total_slack * 0.6
            idle_threshold = max(lower_bound, min(idle_threshold, upper_bound))
        else:
            idle_threshold = 0.0

        # Ensure the no-spot threshold does not exceed the idle threshold.
        nospot_threshold = min(self.slack_no_spot_threshold, idle_threshold)

        # If remaining slack is below the no-spot threshold plus safety buffer,
        # avoid spot entirely and stick to on-demand to eliminate interruption risk.
        if slack_remaining <= nospot_threshold + safety_window:
            return ClusterType.ON_DEMAND

        # Normal decision logic.
        if has_spot:
            # Spot is available and we still have comfortable slack:
            # prefer spot to save cost.
            return ClusterType.SPOT
        else:
            # No spot available: decide between idling and on-demand.
            # If we have plenty of slack above idle_threshold, we can idle
            # and wait for cheaper spot; otherwise, fall back to on-demand.
            if slack_remaining > idle_threshold + safety_window:
                return ClusterType.NONE
            else:
                return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)