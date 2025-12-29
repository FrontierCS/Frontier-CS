import math
from typing import Any, Optional

try:
    from sky_spot.strategies.strategy import Strategy
    from sky_spot.utils import ClusterType
except Exception:
    from enum import Enum

    class ClusterType(Enum):
        SPOT = 1
        ON_DEMAND = 2
        NONE = 3

    class Strategy:
        def __init__(self, args=None):
            self.args = args
            self.env = None


class Solution(Strategy):
    NAME = "cant_be_late_guard_v1"

    def __init__(self, args: Any = None):
        super().__init__(args)
        self.args = args

        self._initialized = False

        # Spot availability run statistics (in steps)
        self._last_has_spot: Optional[bool] = None
        self._run_state: Optional[bool] = None
        self._run_len_steps: int = 0
        self._mean_avail_steps: float = 0.0
        self._mean_unavail_steps: float = 0.0
        self._alpha: float = 0.15

        # Control / hysteresis
        self._pause_steps: int = 0
        self._od_steps: int = 0
        self._force_od: bool = False

        # Defaults derived from env on first step
        self._defaulted: bool = False
        self._default_gap: float = 300.0

    def solve(self, spec_path: str) -> "Solution":
        self._initialized = True
        return self

    @staticmethod
    def _safe_float(x: Any, default: float = 0.0) -> float:
        try:
            v = float(x)
            if math.isfinite(v):
                return v
        except Exception:
            pass
        return default

    def _work_done_seconds(self) -> float:
        t = getattr(self, "task_done_time", None)
        if t is None:
            return 0.0
        if isinstance(t, (int, float)):
            return self._safe_float(t, 0.0)
        if isinstance(t, list):
            if not t:
                return 0.0
            total = 0.0
            # Common variants:
            # - list[float] segment durations
            # - list[(start, end)] segments
            # - list[dict(start=..., end=...)]
            all_num = True
            for seg in t:
                if not isinstance(seg, (int, float)):
                    all_num = False
                    break
            if all_num:
                s = 0.0
                for seg in t:
                    s += self._safe_float(seg, 0.0)
                return max(0.0, s)

            for seg in t:
                if isinstance(seg, (tuple, list)) and len(seg) >= 2:
                    a = self._safe_float(seg[0], 0.0)
                    b = self._safe_float(seg[1], 0.0)
                    total += max(0.0, b - a)
                elif isinstance(seg, dict):
                    if "start" in seg and "end" in seg:
                        a = self._safe_float(seg.get("start"), 0.0)
                        b = self._safe_float(seg.get("end"), 0.0)
                        total += max(0.0, b - a)
                    elif "duration" in seg:
                        total += max(0.0, self._safe_float(seg.get("duration"), 0.0))
                elif isinstance(seg, (int, float)):
                    total += self._safe_float(seg, 0.0)
            return max(0.0, total)
        return 0.0

    def _init_defaults_if_needed(self) -> None:
        if self._defaulted:
            return
        gap = self._safe_float(getattr(getattr(self, "env", None), "gap_seconds", None), self._default_gap)
        if gap <= 0:
            gap = self._default_gap
        self._default_gap = gap

        # Conservative defaults for run lengths if no data:
        # - availability runs tend to be longer than unavailability runs in high-availability traces
        self._mean_avail_steps = max(1.0, 3600.0 / gap)     # ~1 hour
        self._mean_unavail_steps = max(1.0, 900.0 / gap)    # ~15 minutes

        self._defaulted = True

    def _update_spot_run_stats(self, has_spot: bool) -> None:
        if self._last_has_spot is None:
            self._last_has_spot = has_spot
            self._run_state = has_spot
            self._run_len_steps = 1
            return

        if has_spot == self._last_has_spot:
            self._run_len_steps += 1
            return

        # Transition: update mean of previous run
        prev_state = self._last_has_spot
        prev_len = max(1, self._run_len_steps)

        if prev_state:
            self._mean_avail_steps = (1.0 - self._alpha) * self._mean_avail_steps + self._alpha * float(prev_len)
        else:
            self._mean_unavail_steps = (1.0 - self._alpha) * self._mean_unavail_steps + self._alpha * float(prev_len)

        self._last_has_spot = has_spot
        self._run_state = has_spot
        self._run_len_steps = 1

    def _expected_unavail_remaining_seconds(self, gap: float) -> float:
        # Use a conservative residual estimate so we don't over-pause.
        mean_total = max(1.0, self._mean_unavail_steps) * gap
        elapsed = max(0.0, float(self._run_len_steps)) * gap
        # Blend between "remaining to mean" and memoryless-ish mean total.
        rem_to_mean = max(0.0, mean_total - elapsed + gap)
        residual = max(gap, 0.5 * mean_total, rem_to_mean)
        return residual

    def _expected_avail_total_seconds(self, gap: float) -> float:
        return max(1.0, self._mean_avail_steps) * gap

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._init_defaults_if_needed()

        env = getattr(self, "env", None)
        gap = self._safe_float(getattr(env, "gap_seconds", None), self._default_gap)
        if gap <= 0:
            gap = self._default_gap

        elapsed = self._safe_float(getattr(env, "elapsed_seconds", None), 0.0)
        deadline = self._safe_float(getattr(self, "deadline", None), 0.0)
        task_duration = self._safe_float(getattr(self, "task_duration", None), 0.0)
        restart_overhead = self._safe_float(getattr(self, "restart_overhead", None), 0.0)
        if restart_overhead < 0:
            restart_overhead = 0.0

        self._update_spot_run_stats(has_spot)

        # Track consecutive on-demand steps (hysteresis)
        if last_cluster_type == ClusterType.ON_DEMAND:
            self._od_steps += 1
        else:
            self._od_steps = 0

        done = self._work_done_seconds()
        remaining = max(0.0, task_duration - done)

        if remaining <= 1e-9:
            self._force_od = False
            self._pause_steps = 0
            return ClusterType.NONE

        time_left = max(0.0, deadline - elapsed)

        # Hard feasibility guard: if we must start OD now to finish, do it and stick with it.
        od_start_overhead = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else restart_overhead
        min_finish_if_od_now = remaining + od_start_overhead
        if time_left <= min_finish_if_od_now + 1e-6:
            self._force_od = True

        if self._force_od:
            return ClusterType.ON_DEMAND

        # Slack (time that can be spent in overhead / waiting / inefficiencies)
        slack = time_left - remaining
        # Keep some slack reserved for at least one restart (conservative)
        slack_budget = slack - restart_overhead

        # Decide if we can pause briefly during spot outages
        # Keep pauses short; most of the time, make progress on OD when spot is out.
        max_pause_seconds = 0.0
        if slack_budget > 0:
            max_pause_seconds = min(1800.0, 0.30 * slack_budget)  # <= 30 minutes, and <= 30% of slack budget
        max_pause_steps = int(max_pause_seconds // gap) if gap > 0 else 0
        if max_pause_steps < 0:
            max_pause_steps = 0

        # If spot is unavailable, ensure pausing doesn't violate next-step feasibility.
        if not has_spot:
            if time_left - gap <= remaining + restart_overhead + 1e-6:
                return ClusterType.ON_DEMAND

        # Hysteresis: once on OD, stay there for a minimum time to avoid thrashing.
        min_od_run_seconds = max(1800.0, 3.0 * restart_overhead)  # >= 30 minutes
        min_od_run_steps = int(min_od_run_seconds // gap) if gap > 0 else 0

        # Switching from OD to spot is only worth it if the expected available run is long enough.
        expected_avail_total = self._expected_avail_total_seconds(gap)
        min_avail_to_switch = max(3.0 * gap, 2.0 * restart_overhead + 3.0 * gap)

        # Additionally, avoid switching back to spot too late when slack is thin.
        switchback_slack_min = max(2.0 * restart_overhead + 2.0 * gap, 900.0)

        if last_cluster_type == ClusterType.ON_DEMAND:
            if has_spot:
                if self._od_steps < min_od_run_steps:
                    return ClusterType.ON_DEMAND
                if slack_budget > switchback_slack_min and expected_avail_total >= min_avail_to_switch:
                    self._pause_steps = 0
                    return ClusterType.SPOT
            return ClusterType.ON_DEMAND

        if last_cluster_type == ClusterType.SPOT:
            if has_spot:
                self._pause_steps = 0
                return ClusterType.SPOT

            # Spot is out: decide NONE vs OD
            expected_unavail_rem = self._expected_unavail_remaining_seconds(gap)

            # Only pause if we (a) have slack, (b) expected outage is short, and (c) haven't paused too long.
            pause_expected_limit = min(1800.0, max(2.0 * gap, 2.0 * restart_overhead + gap))
            if max_pause_steps > 0 and self._pause_steps < max_pause_steps and expected_unavail_rem <= pause_expected_limit:
                self._pause_steps += 1
                return ClusterType.NONE

            self._pause_steps = 0
            return ClusterType.ON_DEMAND

        # last_cluster_type == NONE (or unexpected)
        if has_spot:
            self._pause_steps = 0
            return ClusterType.SPOT

        expected_unavail_rem = self._expected_unavail_remaining_seconds(gap)
        pause_expected_limit = min(1800.0, max(2.0 * gap, 2.0 * restart_overhead + gap))
        if max_pause_steps > 0 and self._pause_steps < max_pause_steps and expected_unavail_rem <= pause_expected_limit:
            self._pause_steps += 1
            return ClusterType.NONE

        self._pause_steps = 0
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)