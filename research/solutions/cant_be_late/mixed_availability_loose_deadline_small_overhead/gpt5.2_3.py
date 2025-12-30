from __future__ import annotations

import math
from typing import Any, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_v1"

    def __init__(self, args: Optional[Any] = None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except Exception:
                pass

        self._initialized = False
        self._p_ewma = 0.65
        self._alpha = 0.02
        self._steps = 0
        self._spot_steps = 0

        self._cur_outage_steps = 0
        self._max_outage_steps = 0

        self._od_lock = False

        self._overhead_remaining = 0.0
        self._last_choice: Optional[ClusterType] = None

    def solve(self, spec_path: str) -> "Solution":
        return self

    @staticmethod
    def _safe_float(x: Any, default: float = 0.0) -> float:
        try:
            return float(x)
        except Exception:
            return default

    def _get_done_seconds(self) -> float:
        t = getattr(self, "task_done_time", None)
        if not t:
            done = getattr(self.env, "task_done", None)
            if done is None:
                done = getattr(self.env, "task_done_seconds", None)
            if done is None:
                return 0.0
            return self._safe_float(done, 0.0)

        try:
            last = t[-1]
        except Exception:
            return 0.0

        # Case 1: list of cumulative floats
        if isinstance(last, (int, float)):
            try:
                all_num = True
                nondecreasing = True
                prev = None
                for v in t:
                    if not isinstance(v, (int, float)):
                        all_num = False
                        break
                    if prev is not None and v < prev:
                        nondecreasing = False
                    prev = v
                if all_num and nondecreasing:
                    return float(last)
                if all_num:
                    return float(sum(t))
            except Exception:
                return float(last)

        # Case 2: list of (start, end) segments
        if isinstance(last, (tuple, list)) and len(last) == 2:
            try:
                s = 0.0
                for seg in t:
                    if not (isinstance(seg, (tuple, list)) and len(seg) == 2):
                        continue
                    a, b = seg
                    s += float(b) - float(a)
                return max(0.0, s)
            except Exception:
                return 0.0

        # Fallback
        return 0.0

    def _ensure_init(self) -> None:
        if self._initialized:
            return
        self._initialized = True

        gap = self._safe_float(getattr(self.env, "gap_seconds", 60.0), 60.0)
        if gap <= 0:
            gap = 60.0
        self._gap = gap

        self._restart_overhead = self._safe_float(getattr(self, "restart_overhead", 0.0), 0.0)
        self._task_duration = self._safe_float(getattr(self, "task_duration", 0.0), 0.0)
        self._deadline = self._safe_float(getattr(self, "deadline", 0.0), 0.0)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_init()

        elapsed = self._safe_float(getattr(self.env, "elapsed_seconds", 0.0), 0.0)
        time_left = self._deadline - elapsed

        done = self._get_done_seconds()
        remaining = max(0.0, self._task_duration - done)

        if remaining <= 0.0:
            self._last_choice = ClusterType.NONE
            return ClusterType.NONE

        # Update availability statistics
        self._steps += 1
        x = 1.0 if has_spot else 0.0
        self._p_ewma = self._alpha * x + (1.0 - self._alpha) * self._p_ewma
        if has_spot:
            self._spot_steps += 1
            if self._cur_outage_steps > 0:
                if self._cur_outage_steps > self._max_outage_steps:
                    self._max_outage_steps = self._cur_outage_steps
                self._cur_outage_steps = 0
        else:
            self._cur_outage_steps += 1

        # Progress overhead countdown estimate (only while actually running some cluster)
        if self._overhead_remaining > 0.0 and last_cluster_type in (ClusterType.SPOT, ClusterType.ON_DEMAND):
            self._overhead_remaining = max(0.0, self._overhead_remaining - self._gap)

        # Conservative availability estimate
        p_hist = self._spot_steps / max(1, self._steps)
        p_est = min(self._p_ewma, p_hist)
        p_cons = max(0.05, min(0.95, p_est - 0.10))

        gap = self._gap
        restart = self._restart_overhead

        # Convert observed outage to seconds; add baseline to avoid underestimating early
        max_outage_sec = max(0.0, float(self._max_outage_steps) * gap)
        baseline_outage_sec = 2.0 * 3600.0
        hazard_outage_sec = max(max_outage_sec, baseline_outage_sec)

        # Buffers
        hard_finish_buffer = restart + 2.0 * gap
        risk_buffer = hazard_outage_sec + restart + 2.0 * gap

        slack = time_left - remaining

        # If we're too close, lock into on-demand to guarantee completion.
        if time_left <= remaining + hard_finish_buffer:
            self._od_lock = True
        elif slack <= risk_buffer:
            self._od_lock = True

        # If we have locked to on-demand, keep it.
        if self._od_lock:
            # Avoid returning SPOT when has_spot is False (constraint); OD always valid.
            choice = ClusterType.ON_DEMAND
            # Estimate overhead if we are switching compute types (rare after lock)
            if self._last_choice is not None and self._last_choice != choice:
                self._overhead_remaining = restart
            self._last_choice = choice
            return choice

        # Decide action when not locked
        if has_spot:
            # If we previously used OD briefly, switch back to spot only if we have ample slack.
            if last_cluster_type == ClusterType.ON_DEMAND:
                if slack > max(6.0 * 3600.0, 3.0 * risk_buffer) and p_cons >= 0.35:
                    choice = ClusterType.SPOT
                else:
                    choice = ClusterType.ON_DEMAND
            else:
                choice = ClusterType.SPOT

            if self._last_choice is not None and self._last_choice != choice:
                self._overhead_remaining = restart
            self._last_choice = choice
            return choice

        # Spot not available: decide between waiting (NONE) and using OD.
        # Estimate whether spot-only (waiting through outages) is feasible:
        expected_wall_spot_only = remaining / max(p_cons, 0.05)
        feasible_spot_only = expected_wall_spot_only + hazard_outage_sec <= time_left - 2.0 * gap

        # Dynamic waiting: if we have slack, wait up to a limit, then fall back to OD.
        cur_outage_sec = float(self._cur_outage_steps) * gap
        wait_budget_sec = max(0.0, slack - risk_buffer)
        wait_limit_sec = min(wait_budget_sec, hazard_outage_sec)

        if feasible_spot_only and cur_outage_sec < wait_limit_sec:
            choice = ClusterType.NONE
        else:
            choice = ClusterType.ON_DEMAND

        if self._last_choice is not None and self._last_choice != choice and choice != ClusterType.NONE:
            self._overhead_remaining = restart
        self._last_choice = choice
        return choice

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)