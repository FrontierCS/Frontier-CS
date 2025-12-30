import math
from typing import Any, Iterable, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "deadline_guard_spot"

    def __init__(self, args: Any = None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except Exception:
                pass
        self.args = args

        self._prev_choice: Optional[ClusterType] = None
        self._prev_elapsed: Optional[float] = None
        self._overhead_remaining: float = 0.0
        self._committed_od: bool = False

        self._steps: int = 0
        self._spot_avail_steps: int = 0
        self._spot_run_steps: int = 0
        self._spot_interrupts: int = 0

        self._avail_ema: float = 0.2
        self._drop_ema: float = 0.2

    def solve(self, spec_path: str) -> "Solution":
        return self

    @staticmethod
    def _safe_float(x: Any, default: float = 0.0) -> float:
        try:
            if x is None:
                return default
            return float(x)
        except Exception:
            return default

    def _compute_done_work(self) -> float:
        task_duration = self._safe_float(getattr(self, "task_duration", 0.0), 0.0)
        tdt = getattr(self, "task_done_time", None)
        if tdt is None:
            return 0.0
        if isinstance(tdt, (int, float)):
            return max(0.0, min(float(tdt), task_duration)) if task_duration > 0 else max(0.0, float(tdt))

        done = 0.0
        if isinstance(tdt, (list, tuple)):
            if not tdt:
                return 0.0

            first = tdt[0]
            if isinstance(first, (list, tuple)) and len(first) == 2:
                s = 0.0
                for seg in tdt:
                    try:
                        a, b = seg
                        a = float(a)
                        b = float(b)
                        if b > a:
                            s += (b - a)
                    except Exception:
                        continue
                done = s
            elif isinstance(first, dict):
                s = 0.0
                for seg in tdt:
                    if not isinstance(seg, dict):
                        continue
                    for k in ("duration", "work", "done", "seconds"):
                        if k in seg:
                            try:
                                s += float(seg[k])
                                break
                            except Exception:
                                pass
                done = s
            else:
                nums = []
                for v in tdt:
                    if isinstance(v, (int, float)):
                        nums.append(float(v))
                    else:
                        try:
                            nums.append(float(v))
                        except Exception:
                            pass
                if nums:
                    sm = sum(nums)
                    mx = max(nums)
                    if task_duration > 0:
                        if sm <= task_duration * 1.05:
                            done = sm
                        elif mx <= task_duration * 1.05:
                            done = mx
                        else:
                            done = min(sm, mx)
                    else:
                        done = mx
        else:
            try:
                done = float(tdt)
            except Exception:
                done = 0.0

        if task_duration > 0:
            done = max(0.0, min(done, task_duration))
        else:
            done = max(0.0, done)
        return done

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        env = getattr(self, "env", None)
        elapsed = self._safe_float(getattr(env, "elapsed_seconds", 0.0), 0.0)
        gap = self._safe_float(getattr(env, "gap_seconds", 60.0), 60.0)

        deadline = self._safe_float(getattr(self, "deadline", 0.0), 0.0)
        task_duration = self._safe_float(getattr(self, "task_duration", 0.0), 0.0)
        restart_overhead = self._safe_float(getattr(self, "restart_overhead", 0.0), 0.0)

        # Update statistics with current availability info
        self._steps += 1
        if has_spot:
            self._spot_avail_steps += 1

        # Decrement overhead remaining based on previous choice and elapsed delta.
        if self._prev_elapsed is None:
            delta = gap
        else:
            delta = max(0.0, elapsed - self._prev_elapsed)
            if delta <= 0:
                delta = gap

        if self._prev_choice in (ClusterType.SPOT, ClusterType.ON_DEMAND):
            self._overhead_remaining = max(0.0, self._overhead_remaining - delta)
        else:
            self._overhead_remaining = 0.0

        # Spot interruption tracking: if we ran spot last step and now spot is unavailable.
        if last_cluster_type == ClusterType.SPOT:
            self._spot_run_steps += 1
            if not has_spot:
                self._spot_interrupts += 1

        # If spot was the last cluster but now unavailable, the old spot instance is gone.
        # Any remaining overhead in progress on that instance cannot continue.
        if last_cluster_type == ClusterType.SPOT and not has_spot:
            self._overhead_remaining = 0.0

        self._prev_elapsed = elapsed

        # Compute remaining work and time.
        done_work = self._compute_done_work()
        work_left = max(0.0, task_duration - done_work)
        time_left = max(0.0, deadline - elapsed)

        if work_left <= 0.0 or time_left <= 0.0:
            self._prev_choice = ClusterType.NONE
            self._overhead_remaining = 0.0
            return ClusterType.NONE

        # EMA updates (availability, and drop probability conditioned on having spot last step)
        alpha = 0.05
        self._avail_ema = (1.0 - alpha) * self._avail_ema + alpha * (1.0 if has_spot else 0.0)
        if last_cluster_type == ClusterType.SPOT:
            self._drop_ema = (1.0 - alpha) * self._drop_ema + alpha * (0.0 if has_spot else 1.0)

        # Determine what is effectively running at the start of this step.
        if last_cluster_type == ClusterType.ON_DEMAND:
            last_effective = ClusterType.ON_DEMAND
        elif last_cluster_type == ClusterType.SPOT and has_spot:
            last_effective = ClusterType.SPOT
        else:
            last_effective = ClusterType.NONE

        # Minimal time-to-finish if we go (or stay) on-demand from now on.
        if last_effective == ClusterType.ON_DEMAND:
            min_finish_od = work_left + self._overhead_remaining
        else:
            min_finish_od = work_left + restart_overhead

        slack = time_left - min_finish_od

        # Conservative buffers: scale with observed spot volatility.
        drop_est = self._drop_ema
        base_commit = max(6.0 * restart_overhead, 2.0 * gap, 600.0)
        reserve_commit = base_commit + (drop_est * 10.0 * restart_overhead)
        reserve_wait = reserve_commit + gap

        # Commit to on-demand if we're close to the deadline (or already committed).
        if self._committed_od or slack <= reserve_commit or slack <= 0.0:
            self._committed_od = True
            choice = ClusterType.ON_DEMAND
        else:
            if has_spot:
                choice = ClusterType.SPOT
            else:
                if slack > reserve_wait:
                    choice = ClusterType.NONE
                else:
                    self._committed_od = True
                    choice = ClusterType.ON_DEMAND

        # Enforce API requirement: never return SPOT if spot is not available.
        if choice == ClusterType.SPOT and not has_spot:
            choice = ClusterType.ON_DEMAND if not self._committed_od else ClusterType.ON_DEMAND

        # Update overhead state for the choice we are making now.
        if choice == ClusterType.NONE:
            self._overhead_remaining = 0.0
        else:
            if last_effective == choice:
                pass
            else:
                self._overhead_remaining = restart_overhead

        self._prev_choice = choice
        return choice

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)