import math
from typing import Any, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_hedge_v1"

    def __init__(self, args: Optional[Any] = None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except Exception:
                pass

        self._initialized = False

        # Spot availability posterior: Beta(a, b)
        self._spot_a = 3.0
        self._spot_b = 2.0

        # Streak stats (in steps)
        self._last_has_spot: Optional[bool] = None
        self._down_streak = 0
        self._up_streak = 0
        self._ema_down_steps: Optional[float] = None
        self._ema_up_steps: Optional[float] = None
        self._ema_alpha = 0.06

        self._od_commit_until = 0.0

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _get_completed_work_seconds(self) -> float:
        td = getattr(self, "task_done_time", None)
        gap = float(getattr(getattr(self, "env", None), "gap_seconds", 0.0) or 0.0)

        completed = 0.0
        if td is None:
            completed = 0.0
        elif isinstance(td, (int, float)):
            completed = float(td)
        elif isinstance(td, (list, tuple)):
            if len(td) == 0:
                completed = 0.0
            else:
                # If list of tuples (start, end) or (durations)
                try:
                    first = td[0]
                except Exception:
                    first = None

                if isinstance(first, (tuple, list)) and len(first) == 2:
                    s = 0.0
                    for x in td:
                        if isinstance(x, (tuple, list)) and len(x) == 2:
                            try:
                                s += max(0.0, float(x[1]) - float(x[0]))
                            except Exception:
                                pass
                    completed = s
                else:
                    vals = []
                    for x in td:
                        if isinstance(x, (int, float)):
                            vals.append(float(x))
                    if not vals:
                        completed = 0.0
                    else:
                        mx = max(vals)
                        if gap > 0.0 and mx > 1.5 * gap:
                            completed = mx
                        else:
                            completed = sum(vals)
        else:
            completed = 0.0

        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        if task_duration > 0.0:
            if completed < 0.0:
                completed = 0.0
            elif completed > task_duration:
                completed = task_duration
        else:
            completed = max(0.0, completed)
        return completed

    def _update_spot_stats(self, has_spot: bool) -> None:
        if has_spot:
            self._spot_a += 1.0
        else:
            self._spot_b += 1.0

        if self._last_has_spot is None:
            self._last_has_spot = has_spot
            if has_spot:
                self._up_streak = 1
                self._down_streak = 0
            else:
                self._down_streak = 1
                self._up_streak = 0
            return

        if has_spot == self._last_has_spot:
            if has_spot:
                self._up_streak += 1
            else:
                self._down_streak += 1
            return

        # State change
        if self._last_has_spot is False and has_spot is True:
            # down streak ended
            d = max(1, self._down_streak)
            if self._ema_down_steps is None:
                self._ema_down_steps = float(d)
            else:
                self._ema_down_steps = self._ema_alpha * float(d) + (1.0 - self._ema_alpha) * self._ema_down_steps
            self._down_streak = 0
            self._up_streak = 1
        elif self._last_has_spot is True and has_spot is False:
            # up streak ended
            u = max(1, self._up_streak)
            if self._ema_up_steps is None:
                self._ema_up_steps = float(u)
            else:
                self._ema_up_steps = self._ema_alpha * float(u) + (1.0 - self._ema_alpha) * self._ema_up_steps
            self._up_streak = 0
            self._down_streak = 1

        self._last_has_spot = has_spot

    def _spot_lower_bound(self) -> float:
        a, b = self._spot_a, self._spot_b
        n = a + b
        mean = a / n
        var = (a * b) / (n * n * (n + 1.0))
        std = math.sqrt(max(0.0, var))
        conf_mult = 1.3
        return max(0.0, mean - conf_mult * std)

    def _expected_down_seconds(self) -> float:
        gap = float(getattr(self.env, "gap_seconds", 1.0) or 1.0)
        if self._ema_down_steps is None:
            steps = 3.0
        else:
            steps = float(self._ema_down_steps)
        steps = min(max(1.0, steps), 18.0)
        return steps * gap

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not self._initialized:
            self._initialized = True
            self._od_commit_until = 0.0

        self._update_spot_stats(has_spot)

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        gap = float(getattr(self.env, "gap_seconds", 1.0) or 1.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        restart_overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        completed = self._get_completed_work_seconds()
        remaining_work = max(0.0, task_duration - completed)

        if remaining_work <= 0.0:
            return ClusterType.NONE

        remaining_time = max(0.0, deadline - elapsed)
        if remaining_time <= 0.0:
            return ClusterType.ON_DEMAND

        # Buffers / hysteresis
        safety_buffer = max(2.0 * gap, restart_overhead + gap)
        hard_deadline_trigger = deadline - remaining_work - safety_buffer
        if elapsed >= hard_deadline_trigger:
            return ClusterType.ON_DEMAND

        slack = remaining_time - remaining_work
        if slack <= safety_buffer:
            return ClusterType.ON_DEMAND

        required_rate = remaining_work / max(1.0, remaining_time)  # 0..inf, where 1 means full utilization needed on OD
        if required_rate >= 1.0:
            return ClusterType.ON_DEMAND

        # Respect OD commitment to avoid thrashing.
        if last_cluster_type == ClusterType.ON_DEMAND and elapsed < self._od_commit_until:
            if not has_spot:
                return ClusterType.ON_DEMAND
            # Even if spot returns, keep OD unless we have lots of slack.
            if slack < max(3.0 * safety_buffer, 6.0 * gap):
                return ClusterType.ON_DEMAND

        p_lb = self._spot_lower_bound()
        # Conservative adjustment to account for restart/trace variability.
        p_eff = max(0.0, p_lb - 0.03)

        # If spot can't (conservatively) sustain the required rate, use OD.
        if required_rate > p_eff:
            self._od_commit_until = max(self._od_commit_until, elapsed + max(3600.0, 12.0 * gap))
            return ClusterType.ON_DEMAND

        if has_spot:
            # If we can afford spot, use it.
            return ClusterType.SPOT

        # No spot available: decide between waiting and OD.
        expected_down = self._expected_down_seconds()
        wait_margin = 2.0 * gap + restart_overhead
        if slack >= expected_down + wait_margin and required_rate < 0.92:
            return ClusterType.NONE

        self._od_commit_until = max(self._od_commit_until, elapsed + max(3600.0, 12.0 * gap))
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
