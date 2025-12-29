import math
from typing import Any, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "slack_guard_markov_v2"

    def __init__(self, args: Any = None):
        super().__init__(args)
        self._prev_has_spot: Optional[bool] = None

        # Transition counts with Laplace prior (1,1) for each conditional distribution.
        # t01: 0->1, t00: 0->0 ; t10: 1->0, t11: 1->1
        self._t00 = 1.0
        self._t01 = 1.0
        self._t10 = 1.0
        self._t11 = 1.0

        self._off_run_steps = 0
        self._on_run_steps = 0
        self._off_mean_steps = 12.0
        self._on_mean_steps = 48.0

        self._lock_od = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _get_done_seconds(self) -> float:
        # Prefer explicit scalar progress attributes if present.
        for name in ("task_done_seconds", "task_done", "done_seconds", "task_progress_seconds"):
            if hasattr(self, name):
                v = getattr(self, name)
                if isinstance(v, (int, float)) and math.isfinite(v):
                    return max(0.0, float(v))

        tdt = getattr(self, "task_done_time", None)
        td = getattr(self, "task_duration", None)
        task_duration = float(td) if isinstance(td, (int, float)) and math.isfinite(td) else None

        if isinstance(tdt, (int, float)) and math.isfinite(tdt):
            done = max(0.0, float(tdt))
            if task_duration is not None:
                done = min(done, task_duration)
            return done

        if not isinstance(tdt, (list, tuple)) or not tdt:
            return 0.0

        vals = []
        for x in tdt:
            if isinstance(x, (int, float)) and math.isfinite(x):
                vals.append(float(x))
            elif isinstance(x, (list, tuple)) and len(x) >= 2:
                a, b = x[0], x[1]
                if isinstance(a, (int, float)) and isinstance(b, (int, float)) and math.isfinite(a) and math.isfinite(b):
                    a = float(a)
                    b = float(b)
                    vals.append(max(0.0, b - a) if b >= a else max(0.0, b))

        if not vals:
            return 0.0

        s = sum(vals)
        last = vals[-1]

        if task_duration is None:
            return max(0.0, min(s, s if s >= last else last))

        # Heuristic: if sequence is nondecreasing and sum is much larger than duration,
        # interpret as cumulative totals, use last. Otherwise interpret as segments, use sum.
        nondecreasing = True
        for i in range(1, len(vals)):
            if vals[i] + 1e-9 < vals[i - 1]:
                nondecreasing = False
                break

        if nondecreasing and 0.0 <= last <= task_duration + 1e-6 and s > task_duration * 1.05:
            done = last
        else:
            if s <= task_duration * 1.25:
                done = s
            else:
                # Conservative fallback (avoid overestimating progress).
                done = min(max(0.0, min(last, s)), task_duration)

        return max(0.0, min(done, task_duration))

    def _update_spot_stats(self, has_spot: bool) -> None:
        if self._prev_has_spot is not None:
            prev = 1 if self._prev_has_spot else 0
            cur = 1 if has_spot else 0

            if prev == 0 and cur == 0:
                self._t00 += 1.0
            elif prev == 0 and cur == 1:
                self._t01 += 1.0
            elif prev == 1 and cur == 0:
                self._t10 += 1.0
            else:
                self._t11 += 1.0

            if prev == 0 and cur == 1:
                # Off run ended
                if self._off_run_steps > 0:
                    self._off_mean_steps = 0.90 * self._off_mean_steps + 0.10 * float(self._off_run_steps)
                self._off_run_steps = 0
                self._on_run_steps = 1
            elif prev == 1 and cur == 0:
                # On run ended
                if self._on_run_steps > 0:
                    self._on_mean_steps = 0.90 * self._on_mean_steps + 0.10 * float(self._on_run_steps)
                self._on_run_steps = 0
                self._off_run_steps = 1
            else:
                if cur == 1:
                    self._on_run_steps += 1
                    self._off_run_steps = 0
                else:
                    self._off_run_steps += 1
                    self._on_run_steps = 0
        else:
            # Initialize run counters
            self._off_run_steps = 0 if has_spot else 1
            self._on_run_steps = 1 if has_spot else 0

        self._prev_has_spot = has_spot

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._update_spot_stats(has_spot)

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        gap = max(gap, 1e-6)

        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        restart_overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        restart_overhead = max(0.0, restart_overhead)

        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        task_duration = max(0.0, task_duration)

        done = self._get_done_seconds()
        remaining_work = max(0.0, task_duration - done)
        remaining_time = max(0.0, deadline - elapsed)
        slack = remaining_time - remaining_work

        if remaining_work <= 1e-6:
            return ClusterType.NONE

        # Transition probabilities (smoothed)
        p01 = self._t01 / (self._t00 + self._t01)  # P(spot=1 | prev=0)
        p10 = self._t10 / (self._t10 + self._t11)  # P(spot=0 | prev=1)

        # Expected durations in seconds (Markov/geometric assumption)
        exp_off = gap / max(p01, 1e-6)
        exp_on = gap / max(p10, 1e-6)
        exp_off = min(exp_off, max(remaining_time, gap))
        exp_on = min(exp_on, max(remaining_time, gap))

        # Slack reserves (seconds): keep a buffer to absorb restarts / trace volatility.
        reserve_small = max(15.0 * 60.0, 6.0 * restart_overhead + 2.0 * gap)
        reserve_idle = max(60.0 * 60.0, 12.0 * restart_overhead + 6.0 * gap)

        # Lock into on-demand if we're too close to the deadline.
        if (slack <= reserve_small) or (remaining_time <= remaining_work + reserve_small):
            self._lock_od = True

        if self._lock_od:
            return ClusterType.ON_DEMAND if remaining_work > 0 else ClusterType.NONE

        # If spot is available, usually take it. If we're already on OD, switch only if stable enough.
        if has_spot:
            # If we're on OD, require stability and enough slack before switching to avoid thrash/overhead.
            if last_cluster_type == ClusterType.ON_DEMAND:
                min_on_to_switch = max(30.0 * 60.0, 10.0 * restart_overhead + 4.0 * gap)
                if (slack >= reserve_idle) and (exp_on >= min_on_to_switch) and (self._on_mean_steps * gap >= min_on_to_switch):
                    return ClusterType.SPOT
                return ClusterType.ON_DEMAND
            return ClusterType.SPOT

        # No spot available: choose between waiting (NONE) and ON_DEMAND.
        # If already on OD, keep it to avoid extra overhead and ensure progress.
        if last_cluster_type == ClusterType.ON_DEMAND:
            return ClusterType.ON_DEMAND

        off_run_seconds = float(self._off_run_steps) * gap

        # Maximum time we'll tolerate per outage before paying for OD, scaled by available slack.
        # (Don't spend all slack in one long outage.)
        if slack > reserve_idle:
            max_wait = min(6.0 * 3600.0, max(30.0 * 60.0, 0.20 * max(0.0, slack - reserve_idle)))
        else:
            max_wait = 0.0

        # Additional gating using estimated expected outage duration.
        dynamic_guard = reserve_idle + 0.60 * exp_off

        if (slack > dynamic_guard) and (off_run_seconds <= max_wait):
            return ClusterType.NONE

        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)