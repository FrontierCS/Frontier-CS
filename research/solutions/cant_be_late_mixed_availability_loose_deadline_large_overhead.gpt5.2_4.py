import math
from typing import Any, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "deadline_guard_v1"

    def __init__(self, args: Optional[Any] = None):
        super().__init__(args)

        self._lazy_inited = False

        # Spot availability statistics
        self._prev_has_spot: Optional[bool] = None
        self._total_steps = 0
        self._up_steps = 0
        self._up_streak = 0
        self._down_streak = 0
        self._avg_up_steps = 12.0
        self._avg_down_steps = 12.0
        self._ewma_alpha = 0.08

        # Commitment to avoid thrashing during restart overhead
        self._commit_type: Optional[ClusterType] = None
        self._commit_steps_left = 0
        self._commit_steps_default = 1

        # Task progress caching
        self._done_cache = 0.0
        self._done_cache_len = 0

    def solve(self, spec_path: str) -> "Solution":
        return self

    @staticmethod
    def _clamp(x: float, lo: float, hi: float) -> float:
        if x < lo:
            return lo
        if x > hi:
            return hi
        return x

    def _lazy_init(self) -> None:
        if self._lazy_inited:
            return
        self._lazy_inited = True

        gap = float(getattr(self.env, "gap_seconds", 60.0) or 60.0)
        # Prior: 1 hour up/down average in steps
        prior_steps = max(1.0, 3600.0 / gap)
        self._avg_up_steps = prior_steps
        self._avg_down_steps = prior_steps

        ro = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        self._commit_steps_default = max(1, int(math.ceil(ro / gap))) if gap > 0 else 1

    def _parse_done_element(self, x: Any) -> float:
        try:
            if isinstance(x, (int, float)):
                return float(x)
            if isinstance(x, (tuple, list)) and len(x) >= 1:
                if len(x) >= 2 and isinstance(x[0], (int, float)) and isinstance(x[1], (int, float)):
                    a = float(x[0])
                    b = float(x[1])
                    if b >= a:
                        # If it looks like (start, end), use duration
                        return b - a
                    return 0.0
                if isinstance(x[0], (int, float)):
                    return float(x[0])
            if isinstance(x, dict):
                for k in ("duration", "done", "work", "progress"):
                    v = x.get(k, None)
                    if isinstance(v, (int, float)):
                        return float(v)
        except Exception:
            return 0.0
        return 0.0

    def _work_done_seconds(self) -> float:
        # Prefer explicit env attributes if present
        for attr in (
            "task_done_seconds",
            "done_seconds",
            "completed_seconds",
            "progress_seconds",
            "task_progress_seconds",
            "total_done_seconds",
        ):
            v = getattr(self.env, attr, None)
            if isinstance(v, (int, float)):
                return float(v)

        tdt = getattr(self, "task_done_time", None)
        if not isinstance(tdt, list):
            return float(getattr(self.env, "elapsed_work_seconds", 0.0) or 0.0)

        n = len(tdt)
        if n < self._done_cache_len:
            # Reset cache if list was replaced/truncated
            self._done_cache = 0.0
            self._done_cache_len = 0

        for i in range(self._done_cache_len, n):
            self._done_cache += self._parse_done_element(tdt[i])

        self._done_cache_len = n
        return self._done_cache

    def _update_spot_stats(self, has_spot: bool) -> None:
        self._total_steps += 1
        if has_spot:
            self._up_steps += 1

        if self._prev_has_spot is None:
            self._prev_has_spot = has_spot
            if has_spot:
                self._up_streak = 1
                self._down_streak = 0
            else:
                self._down_streak = 1
                self._up_streak = 0
            return

        if has_spot == self._prev_has_spot:
            if has_spot:
                self._up_streak += 1
            else:
                self._down_streak += 1
            return

        # Transition
        if self._prev_has_spot and (not has_spot):
            # up -> down: finalize up streak
            s = float(max(1, self._up_streak))
            self._avg_up_steps = (1.0 - self._ewma_alpha) * self._avg_up_steps + self._ewma_alpha * s
            self._up_streak = 0
            self._down_streak = 1
        elif (not self._prev_has_spot) and has_spot:
            # down -> up: finalize down streak
            s = float(max(1, self._down_streak))
            self._avg_down_steps = (1.0 - self._ewma_alpha) * self._avg_down_steps + self._ewma_alpha * s
            self._down_streak = 0
            self._up_streak = 1

        self._prev_has_spot = has_spot

    def _spot_availability_estimate(self) -> float:
        p_obs = (self._up_steps / self._total_steps) if self._total_steps > 0 else 0.5
        p_run = self._avg_up_steps / (self._avg_up_steps + self._avg_down_steps) if (self._avg_up_steps + self._avg_down_steps) > 0 else 0.5
        p = 0.7 * p_obs + 0.3 * p_run
        return self._clamp(p, 0.02, 0.98)

    def _must_force_on_demand(self, last_cluster_type: ClusterType, time_remaining: float, remaining_work: float, gap: float) -> bool:
        if remaining_work <= 0:
            return False
        ro = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        start_overhead = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else ro
        margin = max(3.0 * gap, ro)
        return time_remaining <= (remaining_work + start_overhead + margin)

    def _set_commit_if_switch(self, last_cluster_type: ClusterType, chosen: ClusterType) -> None:
        if chosen in (ClusterType.SPOT, ClusterType.ON_DEMAND) and chosen != last_cluster_type:
            self._commit_type = chosen
            self._commit_steps_left = self._commit_steps_default
        elif chosen == ClusterType.NONE:
            self._commit_type = None
            self._commit_steps_left = 0

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._lazy_init()

        gap = float(getattr(self.env, "gap_seconds", 60.0) or 60.0)
        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        ro = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        self._update_spot_stats(bool(has_spot))

        done = self._work_done_seconds()
        if not (done >= 0.0):
            done = 0.0
        remaining_work = task_duration - done
        if remaining_work <= 0.0:
            self._commit_type = None
            self._commit_steps_left = 0
            return ClusterType.NONE

        time_remaining = deadline - elapsed
        if time_remaining <= 0.0:
            return ClusterType.NONE

        # Hard guard: if we must go on-demand now to guarantee completion, do it.
        if self._must_force_on_demand(last_cluster_type, time_remaining, remaining_work, gap):
            self._commit_type = ClusterType.ON_DEMAND
            self._commit_steps_left = self._commit_steps_default
            return ClusterType.ON_DEMAND

        # Honor commitment unless invalid; commitment is a soft anti-thrashing mechanism.
        if self._commit_steps_left > 0 and self._commit_type is not None:
            if self._commit_type == ClusterType.SPOT and not has_spot:
                self._commit_steps_left = 0
                self._commit_type = None
            else:
                self._commit_steps_left -= 1
                return self._commit_type

        p_up = self._spot_availability_estimate()
        avg_up_sec = max(gap, float(self._avg_up_steps) * gap)

        # Predict if "spot-only" (run spot when available, otherwise wait) is likely safe.
        overhead_runs = max(0.0, (remaining_work / avg_up_sec) - (1.0 if (has_spot and last_cluster_type == ClusterType.SPOT) else 0.0))
        pred_spot_only_elapsed = (remaining_work / p_up) + overhead_runs * ro

        safety_margin = max(4.0 * gap, 2.0 * ro)

        # Mode selection
        # SpotOnly: SPOT when available, NONE otherwise.
        # Hybrid: SPOT when available (if runs are meaningful), ON_DEMAND otherwise.
        spot_only_safe = pred_spot_only_elapsed <= (time_remaining - safety_margin)

        slack = time_remaining - remaining_work  # time we can afford to waste on outages/overhead

        chosen: ClusterType
        if spot_only_safe:
            if has_spot:
                chosen = ClusterType.SPOT
            else:
                chosen = ClusterType.NONE
        else:
            # Hybrid / OD leaning: keep making progress during outages.
            if has_spot:
                # Switch to spot only if it is likely to stay up long enough to justify restart overhead.
                # (avg_up_sec >= 2*ro) avoids costly micro-runs; slack guard avoids deadline risk.
                if avg_up_sec >= max(2.0 * ro, 3.0 * gap) and slack >= max(3.0 * ro, 6.0 * gap) and p_up >= 0.15:
                    chosen = ClusterType.SPOT
                else:
                    chosen = ClusterType.ON_DEMAND
            else:
                chosen = ClusterType.ON_DEMAND

        if chosen == ClusterType.SPOT and not has_spot:
            chosen = ClusterType.ON_DEMAND if not self._must_force_on_demand(last_cluster_type, time_remaining, remaining_work, gap) else ClusterType.ON_DEMAND

        self._set_commit_if_switch(last_cluster_type, chosen)
        return chosen

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)