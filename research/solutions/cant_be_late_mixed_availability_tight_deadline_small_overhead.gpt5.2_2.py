import math
from typing import Any, Optional


try:
    from sky_spot.strategies.strategy import Strategy
    from sky_spot.utils import ClusterType
except Exception:  # pragma: no cover
    from enum import Enum

    class ClusterType(Enum):
        SPOT = "spot"
        ON_DEMAND = "on_demand"
        NONE = "none"

    class Strategy:
        def __init__(self, *args, **kwargs):
            self.env = None


class _RunningStats:
    __slots__ = ("n", "mean", "m2")

    def __init__(self) -> None:
        self.n = 0
        self.mean = 0.0
        self.m2 = 0.0

    def add(self, x: float) -> None:
        self.n += 1
        d = x - self.mean
        self.mean += d / self.n
        d2 = x - self.mean
        self.m2 += d * d2

    @property
    def var(self) -> float:
        if self.n <= 1:
            return 0.0
        return self.m2 / (self.n - 1)

    @property
    def std(self) -> float:
        v = self.var
        return math.sqrt(v) if v > 0.0 else 0.0


class Solution(Strategy):
    NAME = "cant_be_late_guarded_spot_v1"

    def __init__(self, args: Any = None):
        try:
            super().__init__(args)
        except Exception:
            try:
                super().__init__()
            except Exception:
                pass

        self._last_elapsed: Optional[float] = None
        self._prev_has_spot: Optional[bool] = None
        self._run_len: float = 0.0

        self._down_stats = _RunningStats()
        self._up_stats = _RunningStats()

        self._total_steps = 0
        self._spot_steps = 0

        self._locked_to_od = False
        self._od_since: Optional[float] = None

    def solve(self, spec_path: str) -> "Solution":
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

    def _reset_episode_state(self) -> None:
        self._last_elapsed = None
        self._prev_has_spot = None
        self._run_len = 0.0
        self._down_stats = _RunningStats()
        self._up_stats = _RunningStats()
        self._total_steps = 0
        self._spot_steps = 0
        self._locked_to_od = False
        self._od_since = None

    def _update_runs(self, has_spot: bool, gap: float) -> None:
        if self._prev_has_spot is None:
            self._prev_has_spot = has_spot
            self._run_len = gap
            return

        if has_spot == self._prev_has_spot:
            self._run_len += gap
            return

        finished_len = self._run_len
        if self._prev_has_spot:
            self._up_stats.add(finished_len)
        else:
            self._down_stats.add(finished_len)

        self._prev_has_spot = has_spot
        self._run_len = gap

    def _current_down_run_len(self, has_spot: bool) -> float:
        if has_spot:
            return 0.0
        if self._prev_has_spot is False:
            return self._run_len
        return 0.0

    def _availability_estimate(self) -> float:
        if self._total_steps <= 0:
            return 0.5
        p = self._spot_steps / self._total_steps
        # Lower-confidence bound to be conservative early on.
        n = self._total_steps
        se = math.sqrt(max(p * (1.0 - p), 0.0) / max(n, 1))
        lcb = max(0.01, p - 1.0 * se)
        return lcb

    def _done_seconds(self) -> float:
        # Prefer any direct attribute if present
        for attr in ("task_done_seconds", "task_done", "done_seconds", "completed_seconds"):
            v = getattr(self, attr, None)
            if v is not None:
                fv = self._safe_float(v, default=-1.0)
                if fv >= 0.0:
                    return fv

        env = getattr(self, "env", None)
        if env is not None:
            for attr in ("task_done_seconds", "task_done", "done_seconds", "completed_seconds"):
                v = getattr(env, attr, None)
                if v is not None:
                    fv = self._safe_float(v, default=-1.0)
                    if fv >= 0.0:
                        return fv

        tdt = getattr(self, "task_done_time", None)
        if tdt is None:
            return 0.0

        if isinstance(tdt, (int, float)):
            return max(0.0, float(tdt))

        if isinstance(tdt, (list, tuple)):
            if not tdt:
                return 0.0

            # If list of (start, end) segments:
            try:
                if isinstance(tdt[0], (list, tuple)) and len(tdt[0]) == 2:
                    s = 0.0
                    for seg in tdt:
                        if not (isinstance(seg, (list, tuple)) and len(seg) == 2):
                            continue
                        a = self._safe_float(seg[0], 0.0)
                        b = self._safe_float(seg[1], 0.0)
                        if b > a:
                            s += (b - a)
                    return max(0.0, s)
            except Exception:
                pass

            # If list of numeric segments or cumulative markers:
            nums = []
            for x in tdt:
                if isinstance(x, (int, float)):
                    nums.append(float(x))
                else:
                    try:
                        nums.append(float(x))
                    except Exception:
                        pass
            if not nums:
                return 0.0

            s = sum(nums)
            last = nums[-1]
            nondecreasing = all(nums[i] <= nums[i + 1] for i in range(len(nums) - 1))

            td = self._safe_float(getattr(self, "task_duration", 0.0), 0.0)
            if nondecreasing and td > 0.0:
                # Heuristic: if summing clearly overcounts, treat as cumulative.
                if s > td * 1.05 or s > last * 1.2:
                    return max(0.0, min(last, td))

            return max(0.0, min(s, td if td > 0.0 else s))

        return 0.0

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        env = getattr(self, "env", None)
        elapsed = self._safe_float(getattr(env, "elapsed_seconds", 0.0), 0.0)
        gap = self._safe_float(getattr(env, "gap_seconds", 60.0), 60.0)

        # Detect new episode / reset
        if self._last_elapsed is None:
            self._last_elapsed = elapsed
        elif elapsed < self._last_elapsed - 1e-6:
            self._reset_episode_state()
            self._last_elapsed = elapsed
        else:
            self._last_elapsed = elapsed

        # Update availability stats/runs for this step
        self._total_steps += 1
        if has_spot:
            self._spot_steps += 1
        self._update_runs(has_spot, gap)

        task_duration = self._safe_float(getattr(self, "task_duration", 0.0), 0.0)
        deadline = self._safe_float(getattr(self, "deadline", 0.0), 0.0)
        restart_overhead = self._safe_float(getattr(self, "restart_overhead", 0.0), 0.0)

        done = self._done_seconds()
        remaining_work = max(0.0, task_duration - done)
        remaining_time = max(0.0, deadline - elapsed)
        slack = remaining_time - remaining_work

        if remaining_work <= 0.0:
            return ClusterType.NONE

        # Conservative buffers
        # lock_slack: once slack is low, commit to on-demand to guarantee deadline.
        lock_slack = max(2700.0, 18.0 * restart_overhead + 4.0 * gap)  # ~45 minutes minimum
        # panic_slack: even more conservative for finishing safely with overhead.
        panic_slack = max(900.0, 6.0 * restart_overhead + 2.0 * gap)  # ~15 minutes minimum

        # If we are already too tight, go OD immediately.
        if remaining_time <= remaining_work + panic_slack:
            self._locked_to_od = True

        if slack <= lock_slack:
            self._locked_to_od = True

        # Estimate choppiness: if up periods are shorter than overhead, spot is inefficient/risky.
        up_mean = self._up_stats.mean if self._up_stats.n > 0 else None
        down_mean = self._down_stats.mean if self._down_stats.n > 0 else None

        spot_choppy = False
        if up_mean is not None and up_mean > 0.0:
            spot_choppy = up_mean < max(2.0 * restart_overhead, 1.5 * gap)

        # Allow switching back from OD to SPOT only when well safe, to save cost.
        switchback_slack = max(lock_slack + 7200.0, 3.0 * lock_slack)  # at least +2 hours
        if self._locked_to_od and slack > switchback_slack and has_spot and not spot_choppy:
            # Only unlock if we are comfortably safe again (rare, but prevents over-committing).
            self._locked_to_od = False

        if self._locked_to_od:
            self._od_since = elapsed if self._od_since is None else self._od_since
            return ClusterType.ON_DEMAND

        # Not locked: prefer SPOT when it's available, unless extremely choppy and slack isn't huge.
        if has_spot:
            if spot_choppy and slack < max(3.0 * lock_slack, 10800.0):  # < 3*lock or < 3 hours
                self._od_since = elapsed if self._od_since is None else self._od_since
                return ClusterType.ON_DEMAND
            return ClusterType.SPOT

        # Spot not available: either wait (NONE) or run OD.
        allowable_wait = slack - lock_slack
        if allowable_wait <= 0.0:
            self._od_since = elapsed if self._od_since is None else self._od_since
            return ClusterType.ON_DEMAND

        # Predict remaining downtime length conservatively using down run stats.
        current_down = self._current_down_run_len(has_spot=False)
        if self._down_stats.n <= 0:
            pred_total_down = max(2.0 * gap, 5.0 * restart_overhead)
        else:
            pred_total_down = self._down_stats.mean + 1.0 * self._down_stats.std
            pred_total_down = max(pred_total_down, self._down_stats.mean)

        pred_remaining_down = max(0.0, pred_total_down - current_down)

        # Also consider overall availability: if very low, prefer OD rather than waiting too long.
        p_lcb = self._availability_estimate()
        very_low_availability = p_lcb < 0.12  # empirically cautious

        if (pred_remaining_down <= allowable_wait) and not very_low_availability:
            return ClusterType.NONE

        self._od_since = elapsed if self._od_since is None else self._od_since
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)