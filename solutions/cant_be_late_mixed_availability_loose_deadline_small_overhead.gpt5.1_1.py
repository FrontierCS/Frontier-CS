import math
from typing import Any

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_hedging"

    def solve(self, spec_path: str) -> "Solution":
        if not hasattr(self, "_cbh_initialized"):
            self._cbh_initialized = False
        return self

    def _initialize_if_needed(self) -> None:
        if getattr(self, "_cbh_initialized", False):
            return

        # Initial slack: how much wall-clock time we can "waste" (idle + overhead)
        # while still being able to finish the remaining work on pure on-demand.
        self._cbh_initial_slack = max(self.deadline - self.task_duration, 0.0)

        # Cached completed work to avoid repeatedly summing a growing list.
        self._cbh_cached_done = 0.0
        self._cbh_last_task_done_len = 0

        # Choose policy aggressiveness based on relative slack.
        if self._cbh_initial_slack <= 0 or self.task_duration <= 0:
            # No slack: be maximally conservative.
            self._cbh_aggressive_frac = 0.0
            self._cbh_switch_od_frac = 0.0
        else:
            ratio = self._cbh_initial_slack / self.task_duration
            # Heuristic thresholds tuned by slack ratio.
            if ratio >= 0.4:
                aggressive = 0.4
                switch_od = 0.75
            elif ratio >= 0.25:
                aggressive = 0.25
                switch_od = 0.6
            elif ratio >= 0.15:
                aggressive = 0.15
                switch_od = 0.5
            else:
                aggressive = 0.05
                switch_od = 0.35

            if switch_od < aggressive + 0.05:
                switch_od = min(0.9, aggressive + 0.05)

            self._cbh_aggressive_frac = aggressive
            self._cbh_switch_od_frac = switch_od

        self._cbh_initialized = True

    def _update_completed_work_cache(self) -> float:
        """Incrementally maintain total completed work."""
        lst = self.task_done_time
        current_len = len(lst)
        if current_len > self._cbh_last_task_done_len:
            new_segments = lst[self._cbh_last_task_done_len : current_len]
            self._cbh_cached_done += float(sum(new_segments))
            self._cbh_last_task_done_len = current_len
        # Clamp to task_duration to avoid tiny numerical negatives later.
        if self._cbh_cached_done > self.task_duration:
            self._cbh_cached_done = self.task_duration
        return self._cbh_cached_done

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._initialize_if_needed()

        # Update completed work.
        done = self._update_completed_work_cache()
        remaining = self.task_duration - done

        # If task is finished (or very close), do nothing.
        if remaining <= 0.0:
            return ClusterType.NONE

        # Current time and slack.
        t = self.env.elapsed_seconds
        slack = self.deadline - t - remaining

        # If no initial slack, always use on-demand to avoid any extra risk.
        if self._cbh_initial_slack <= 0.0:
            return ClusterType.ON_DEMAND

        # If we've already exhausted all slack, switch to on-demand.
        if slack <= 0.0:
            return ClusterType.ON_DEMAND

        # Slack spent so far (idle + restart overhead).
        spent = self._cbh_initial_slack - slack
        if spent < 0.0:
            spent = 0.0
        elif spent > self._cbh_initial_slack:
            spent = self._cbh_initial_slack

        spent_frac = spent / self._cbh_initial_slack if self._cbh_initial_slack > 0.0 else 1.0

        # Time resolution of the environment.
        gap = getattr(self.env, "gap_seconds", 0.0) or 0.0

        # High-slack (aggressive) region:
        # - Use SPOT whenever available.
        # - When SPOT is unavailable, idle (NONE) to save cost,
        #   but never idle so much that we can no longer recover with pure OD.
        if spent_frac < self._cbh_aggressive_frac:
            if has_spot:
                return ClusterType.SPOT
            else:
                # Ensure we can afford to waste a whole gap of time.
                if slack - gap <= 0.0:
                    return ClusterType.ON_DEMAND
                return ClusterType.NONE

        # Medium-slack (balanced) region:
        # - Use SPOT when available.
        # - When SPOT is down, immediately fall back to OD to avoid further slack loss.
        if spent_frac < self._cbh_switch_od_frac:
            if has_spot:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND

        # Low-slack (conservative/panic) region:
        # - Commit to ON_DEMAND only, ignoring SPOT to eliminate preemption risk.
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser: Any) -> "Solution":
        args, _ = parser.parse_known_args()
        return cls(args)
