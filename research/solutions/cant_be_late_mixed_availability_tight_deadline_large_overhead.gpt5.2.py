from __future__ import annotations

import math
from typing import Any, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_adaptive_v1"

    def __init__(self, args: Optional[Any] = None):
        super().__init__(args)

        # Progress tracking
        self._done_idx = 0
        self._done_sum = 0.0

        # Spot availability statistics (trace-based, not decision-based)
        self._prev_has_spot: Optional[bool] = None
        self._cur_up = 0.0
        self._cur_down = 0.0
        self._up_sum = 0.0
        self._down_sum = 0.0
        self._up_count = 0
        self._down_count = 0
        self._down_transitions = 0

        # Decision state
        self._permanent_od = False
        self._od_cooldown_steps = 0
        self._wait_used = 0.0
        self._outage_waited = 0.0

        # Tunables (seconds)
        self._default_uptime = 4.0 * 3600.0
        self._default_downtime = 0.5 * 3600.0
        self._prior_uptime_count = 1.0
        self._prior_downtime_count = 1.0

        # Down-transition prior: roughly 1 interruption every 5 hours -> 0.2/h
        self._prior_down_rate_hours = 5.0
        self._prior_down_transitions = 1.0

        # Waiting policy
        self._wait_budget = 1.0 * 3600.0
        self._max_wait_per_outage = 0.5 * 3600.0
        self._max_avg_downtime_to_wait = 0.75 * 3600.0

        # Switching policy
        self._min_avg_uptime_to_use_spot = 0.25 * 3600.0
        self._min_avg_uptime_to_switch_from_od = 1.0 * 3600.0
        self._min_slack_to_switch_from_od = 1.5 * 3600.0

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _update_done_work(self) -> float:
        tdt = getattr(self, "task_done_time", None)
        if not tdt:
            return self._done_sum
        try:
            n = len(tdt)
        except Exception:
            return self._done_sum
        if n <= self._done_idx:
            return self._done_sum

        for i in range(self._done_idx, n):
            x = tdt[i]
            seg = 0.0
            try:
                if isinstance(x, (int, float)):
                    seg = float(x)
                elif isinstance(x, (tuple, list)) and len(x) == 2 and isinstance(x[0], (int, float)) and isinstance(x[1], (int, float)):
                    seg = float(x[1]) - float(x[0])
                else:
                    seg = 0.0
            except Exception:
                seg = 0.0
            if seg > 0:
                self._done_sum += seg

        self._done_idx = n
        return self._done_sum

    def _update_availability_stats(self, has_spot: bool, gap: float) -> None:
        if self._prev_has_spot is None:
            self._prev_has_spot = has_spot
            if has_spot:
                self._cur_up = gap
                self._cur_down = 0.0
            else:
                self._cur_down = gap
                self._cur_up = 0.0
            return

        prev = self._prev_has_spot
        if has_spot == prev:
            if has_spot:
                self._cur_up += gap
            else:
                self._cur_down += gap
            return

        # Transition
        if prev and not has_spot:
            # Up -> Down
            self._down_transitions += 1
            self._up_sum += self._cur_up
            self._up_count += 1
            self._cur_up = 0.0
            self._cur_down = gap
        elif (not prev) and has_spot:
            # Down -> Up
            self._down_sum += self._cur_down
            self._down_count += 1
            self._cur_down = 0.0
            self._cur_up = gap
        else:
            # Should not happen
            if has_spot:
                self._cur_up = gap
                self._cur_down = 0.0
            else:
                self._cur_down = gap
                self._cur_up = 0.0

        self._prev_has_spot = has_spot

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        env = getattr(self, "env", None)
        elapsed = float(getattr(env, "elapsed_seconds", 0.0) if env is not None else 0.0)
        gap = float(getattr(env, "gap_seconds", 60.0) if env is not None else 60.0)

        self._update_availability_stats(has_spot, gap)
        done = self._update_done_work()

        task_duration = float(getattr(self, "task_duration", 0.0))
        deadline = float(getattr(self, "deadline", 0.0))
        restart = float(getattr(self, "restart_overhead", 0.0))

        remaining_work = max(0.0, task_duration - done)
        time_left = max(0.0, deadline - elapsed)
        slack = time_left - remaining_work

        # Smoothed averages with simple priors
        avg_up = (self._up_sum + self._prior_uptime_count * self._default_uptime) / (self._up_count + self._prior_uptime_count)
        avg_down = (self._down_sum + self._prior_downtime_count * self._default_downtime) / (self._down_count + self._prior_downtime_count)

        elapsed_hours = max(1e-6, elapsed / 3600.0)
        down_rate_per_hour = (self._down_transitions + self._prior_down_transitions) / (elapsed_hours + self._prior_down_rate_hours)

        expected_future_interruptions = down_rate_per_hour * max(0.0, remaining_work / 3600.0)

        safety_slack = max(2.0 * restart, 3.0 * gap) + 10.0 * 60.0
        end_margin = restart + 2.0 * gap

        if slack <= safety_slack or elapsed >= (deadline - remaining_work - end_margin):
            self._permanent_od = True

        if restart > 1e-9:
            allowed_interruptions = max(0.0, (slack - safety_slack) / restart)
        else:
            allowed_interruptions = float("inf")

        keep_spot_ok = (
            (expected_future_interruptions + 1.0) <= allowed_interruptions
            and avg_up >= self._min_avg_uptime_to_use_spot
        )

        if self._od_cooldown_steps > 0:
            self._od_cooldown_steps -= 1

        if self._permanent_od:
            return ClusterType.ON_DEMAND

        if not has_spot:
            can_wait = (
                slack > (safety_slack + 0.5 * 3600.0)
                and self._wait_used < self._wait_budget
                and avg_down <= self._max_avg_downtime_to_wait
                and self._outage_waited < self._max_wait_per_outage
            )
            if can_wait:
                self._wait_used += gap
                self._outage_waited += gap
                return ClusterType.NONE

            self._outage_waited = 0.0
            # When spot is unavailable, prefer on-demand to keep progressing.
            return ClusterType.ON_DEMAND

        # has_spot == True
        self._outage_waited = 0.0

        if not keep_spot_ok:
            # If risk is too high, stick to on-demand from now on.
            if slack <= safety_slack + 2.0 * restart:
                self._permanent_od = True
            return ClusterType.ON_DEMAND

        # If we recently had instability, avoid immediate switching OD->SPOT (churn).
        if last_cluster_type == ClusterType.ON_DEMAND:
            if self._od_cooldown_steps > 0:
                return ClusterType.ON_DEMAND
            if slack >= self._min_slack_to_switch_from_od and avg_up >= self._min_avg_uptime_to_switch_from_od:
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND

        if last_cluster_type == ClusterType.NONE:
            # Prefer spot if available and safe.
            return ClusterType.SPOT

        # last_cluster_type == SPOT or other
        return ClusterType.SPOT

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)