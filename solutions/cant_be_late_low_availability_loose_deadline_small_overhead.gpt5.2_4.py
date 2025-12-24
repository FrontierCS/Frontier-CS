import math
from typing import Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "deadline_aware_hysteresis_v1"

    def __init__(self, args=None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except Exception:
                pass

        self._initialized = False
        self._prev_elapsed = 0.0

        self._commit_od = False

        self._ema_p = 0.2
        self._ema_alpha: Optional[float] = None

        self._last_has_spot: Optional[bool] = None
        self._run_len_steps = 0
        self._avg_spot_run_steps = 2.0
        self._avg_nospot_run_steps = 6.0

        self._idle_run_steps = 0
        self._total_idle_seconds = 0.0

        self._od_block_steps_remaining = 0

        self._done_cache_len = 0
        self._done_cache_sum = 0.0

        self._initial_slack_seconds: Optional[float] = None
        self._max_idle_cap_seconds: Optional[float] = None
        self._idle_budget_seconds: Optional[float] = None

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _get_done_seconds(self) -> float:
        lst = getattr(self, "task_done_time", None)
        if not lst:
            self._done_cache_len = 0
            self._done_cache_sum = 0.0
            return 0.0
        try:
            l = len(lst)
        except Exception:
            try:
                v = float(lst)
            except Exception:
                v = 0.0
            self._done_cache_len = 1
            self._done_cache_sum = v
            return v

        if l == self._done_cache_len:
            return self._done_cache_sum
        if l > self._done_cache_len:
            try:
                add = sum(lst[self._done_cache_len :])
            except Exception:
                add = sum(float(x) for x in lst[self._done_cache_len :])
            self._done_cache_sum += add
            self._done_cache_len = l
            return self._done_cache_sum

        try:
            s = sum(lst)
        except Exception:
            s = sum(float(x) for x in lst)
        self._done_cache_sum = s
        self._done_cache_len = l
        return s

    def _update_spot_stats(self, has_spot: bool, gap: float) -> None:
        if self._ema_alpha is None:
            # Half-life around ~2 hours for stability across gap sizes.
            self._ema_alpha = 1.0 - math.exp(-max(gap, 1.0) / 7200.0)
            self._ema_alpha = min(0.25, max(0.005, self._ema_alpha))

        a = self._ema_alpha
        self._ema_p = (1.0 - a) * self._ema_p + a * (1.0 if has_spot else 0.0)
        self._ema_p = min(0.98, max(0.02, self._ema_p))

        if self._last_has_spot is None:
            self._last_has_spot = has_spot
            self._run_len_steps = 1
            return

        if has_spot == self._last_has_spot:
            self._run_len_steps += 1
            return

        # Run ended; update corresponding average.
        w = 0.2
        if self._last_has_spot:
            self._avg_spot_run_steps = (1.0 - w) * self._avg_spot_run_steps + w * float(self._run_len_steps)
            self._avg_spot_run_steps = min(2000.0, max(1.0, self._avg_spot_run_steps))
        else:
            self._avg_nospot_run_steps = (1.0 - w) * self._avg_nospot_run_steps + w * float(self._run_len_steps)
            self._avg_nospot_run_steps = min(2000.0, max(1.0, self._avg_nospot_run_steps))

        self._last_has_spot = has_spot
        self._run_len_steps = 1

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        now = float(getattr(self.env, "elapsed_seconds", 0.0))
        gap = float(getattr(self.env, "gap_seconds", 60.0))
        gap = max(1e-6, gap)

        if not self._initialized:
            self._initialized = True
            self._prev_elapsed = now
            self._idle_run_steps = 0
            self._od_block_steps_remaining = 0
            self._total_idle_seconds = 0.0

            try:
                slack0 = float(self.deadline) - float(self.task_duration)
            except Exception:
                slack0 = 0.0
            slack0 = max(0.0, slack0)
            self._initial_slack_seconds = slack0
            self._idle_budget_seconds = 0.8 * slack0
            self._max_idle_cap_seconds = min(8.0 * 3600.0, 0.6 * slack0) if slack0 > 0 else 0.0
        else:
            delta = now - self._prev_elapsed
            if not (delta > 0.0):
                delta = gap
            self._prev_elapsed = now

            if last_cluster_type == ClusterType.NONE:
                self._idle_run_steps += 1
                self._total_idle_seconds += delta
            else:
                self._idle_run_steps = 0

            if last_cluster_type == ClusterType.ON_DEMAND:
                if self._od_block_steps_remaining > 0:
                    self._od_block_steps_remaining -= 1
            else:
                self._od_block_steps_remaining = 0

        self._update_spot_stats(has_spot, gap)

        done = self._get_done_seconds()
        try:
            task_dur = float(self.task_duration)
        except Exception:
            task_dur = 0.0
        remaining = max(0.0, task_dur - done)

        try:
            deadline = float(self.deadline)
        except Exception:
            deadline = 0.0
        time_left = deadline - now

        if remaining <= 1e-9:
            return ClusterType.NONE

        if time_left <= 0.0:
            return ClusterType.NONE

        try:
            overhead = float(self.restart_overhead)
        except Exception:
            overhead = 0.0
        overhead = max(0.0, overhead)

        slack = time_left - remaining
        safety = overhead + gap

        # Hard safety: if we're too tight, commit to on-demand regardless.
        if slack <= 4.0 * safety or time_left <= remaining + 4.0 * safety:
            self._commit_od = True
        if self._commit_od:
            return ClusterType.ON_DEMAND

        # If we are in a short on-demand block, keep it unless a clearly worthwhile spot window appears.
        if last_cluster_type == ClusterType.ON_DEMAND and self._od_block_steps_remaining > 0:
            if has_spot:
                exp_spot_run_sec = self._avg_spot_run_steps * gap
                if exp_spot_run_sec >= 2.0 * overhead and slack > 8.0 * safety:
                    self._od_block_steps_remaining = 0
                    return ClusterType.SPOT
            return ClusterType.ON_DEMAND

        if has_spot:
            # If on-demand was used, switch to spot only if the spot runs tend to be long enough.
            if last_cluster_type == ClusterType.ON_DEMAND:
                exp_spot_run_sec = self._avg_spot_run_steps * gap
                if exp_spot_run_sec >= 2.0 * overhead and slack > 6.0 * safety:
                    return ClusterType.SPOT
                return ClusterType.ON_DEMAND
            return ClusterType.SPOT

        # No spot available: decide between waiting (NONE) and on-demand.

        # If already on on-demand, usually keep going (avoid start/stop overhead and lost time).
        if last_cluster_type == ClusterType.ON_DEMAND:
            return ClusterType.ON_DEMAND

        # If slack is tight, go on-demand.
        if slack <= 2.0 * safety:
            self._od_block_steps_remaining = max(0, int(math.ceil(900.0 / gap)) - 1)  # ~15 min block
            return ClusterType.ON_DEMAND

        p = self._ema_p
        # Expected time to next spot; combine global rate and typical no-spot run length.
        exp_wait_sec = max(gap / max(0.02, p), 0.7 * self._avg_nospot_run_steps * gap)

        idle_budget_left = max(0.0, (self._idle_budget_seconds or 0.0) - self._total_idle_seconds)
        max_idle_cap = self._max_idle_cap_seconds or 0.0

        allow_idle_sec = min(exp_wait_sec, max(0.0, slack - 5.0 * safety), idle_budget_left, max_idle_cap)

        # If we've already waited long enough in this no-spot stretch, switch to on-demand.
        if self._idle_run_steps * gap < allow_idle_sec:
            return ClusterType.NONE

        self._od_block_steps_remaining = max(0, int(math.ceil(1800.0 / gap)) - 1)  # ~30 min block
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
