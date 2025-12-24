import math
from typing import Optional

try:
    from sky_spot.strategies.strategy import Strategy
    from sky_spot.utils import ClusterType
except Exception:  # pragma: no cover
    from enum import Enum

    class ClusterType(Enum):
        SPOT = "SPOT"
        ON_DEMAND = "ON_DEMAND"
        NONE = "NONE"

    class _DummyEnv:
        elapsed_seconds = 0.0
        gap_seconds = 60.0
        cluster_type = ClusterType.NONE

    class Strategy:
        def __init__(self, *args, **kwargs):
            self.env = _DummyEnv()
            self.task_duration = 0.0
            self.task_done_time = []
            self.deadline = 0.0
            self.restart_overhead = 0.0


class Solution(Strategy):
    NAME = "cant_be_late_adaptive_v1"

    def __init__(self, *args, **kwargs):
        try:
            super().__init__(*args, **kwargs)
        except TypeError:
            try:
                super().__init__()
            except Exception:
                pass
        self._reset_state()

    def _reset_state(self):
        self._last_has_spot_seen: Optional[bool] = None
        self._streak_is_up: Optional[bool] = None
        self._streak_len_steps: int = 0

        self._total_steps: int = 0
        self._up_steps: int = 0
        self._down_steps: int = 0
        self._up_to_down: int = 0
        self._down_to_up: int = 0

        self._ema_up_steps: Optional[float] = None
        self._ema_down_steps: Optional[float] = None
        self._ema_alpha: float = 0.08

        self._done_sum: float = 0.0
        self._done_len: int = 0

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _update_trace_stats(self, has_spot: bool):
        self._total_steps += 1
        if has_spot:
            self._up_steps += 1
        else:
            self._down_steps += 1

        if self._last_has_spot_seen is None:
            self._last_has_spot_seen = has_spot
            self._streak_is_up = has_spot
            self._streak_len_steps = 1
            return

        if has_spot == self._last_has_spot_seen:
            self._streak_len_steps += 1
        else:
            # close previous streak
            prev_len = self._streak_len_steps
            if self._streak_is_up:
                if self._ema_up_steps is None:
                    self._ema_up_steps = float(prev_len)
                else:
                    self._ema_up_steps = (1.0 - self._ema_alpha) * self._ema_up_steps + self._ema_alpha * float(prev_len)
                self._up_to_down += 1
            else:
                if self._ema_down_steps is None:
                    self._ema_down_steps = float(prev_len)
                else:
                    self._ema_down_steps = (1.0 - self._ema_alpha) * self._ema_down_steps + self._ema_alpha * float(prev_len)
                self._down_to_up += 1

            self._last_has_spot_seen = has_spot
            self._streak_is_up = has_spot
            self._streak_len_steps = 1

    def _get_done_work(self) -> float:
        td = getattr(self, "task_done_time", None)
        if not td:
            self._done_sum = 0.0
            self._done_len = 0
            return 0.0

        try:
            n = len(td)
        except Exception:
            try:
                return float(sum(td))
            except Exception:
                return 0.0

        if n < self._done_len:
            try:
                self._done_sum = float(sum(td))
            except Exception:
                self._done_sum = 0.0
            self._done_len = n
            return self._done_sum

        if n > self._done_len:
            try:
                self._done_sum += float(sum(td[self._done_len :]))
            except Exception:
                try:
                    self._done_sum = float(sum(td))
                except Exception:
                    self._done_sum = 0.0
            self._done_len = n

        return self._done_sum

    def _hazard_up_to_down(self) -> float:
        # Probability that an "up" step ends (up->down) at the next boundary.
        # Smoothed to avoid early extreme estimates.
        return (self._up_to_down + 1.0) / (self._up_steps + 2.0)

    def _expected_up_seconds(self, gap: float) -> float:
        h = self._hazard_up_to_down()
        h = min(0.999, max(0.001, h))
        exp_up_steps = (1.0 - h) / h
        return exp_up_steps * gap

    def _buffers(self, remaining: float, gap: float, overhead: float) -> tuple[float, float, float, float]:
        # base_buffer: always keep some headroom for at least a few restarts + discretization
        base_buffer = max(2.0 * gap, 6.0 * overhead, 120.0)

        h = self._hazard_up_to_down()
        steps_needed = remaining / max(gap, 1e-9)
        expected_restarts = h * steps_needed
        expected_overhead = expected_restarts * overhead

        min_slack_needed = expected_overhead + base_buffer

        reserve_wait = max(gap, 2.0 * overhead, 60.0)
        urgent_slack = max(4.0 * overhead + gap, base_buffer * 0.75)

        return min_slack_needed, reserve_wait, urgent_slack, expected_overhead

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._update_trace_stats(has_spot)

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0))
        gap = float(getattr(self.env, "gap_seconds", 60.0))
        overhead = float(getattr(self, "restart_overhead", 0.0))
        deadline = float(getattr(self, "deadline", 0.0))
        task_duration = float(getattr(self, "task_duration", 0.0))

        done = self._get_done_work()
        remaining = max(0.0, task_duration - done)
        if remaining <= 0.0:
            return ClusterType.NONE

        time_left = deadline - elapsed
        if time_left <= 0.0:
            return ClusterType.NONE

        slack = time_left - remaining

        min_slack_needed, reserve_wait, urgent_slack, _ = self._buffers(remaining, gap, overhead)

        # Absolute "don't miss" guard: if we cannot afford any extra overhead from a switch,
        # avoid switching away from a currently-working spot when it is available.
        if slack <= overhead + gap:
            if has_spot and last_cluster_type == ClusterType.SPOT:
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND

        # Spot unavailable: decide between waiting and on-demand
        if not has_spot:
            if last_cluster_type == ClusterType.ON_DEMAND:
                return ClusterType.ON_DEMAND

            # Spend slack only if we are above a conservative overhead budget.
            if slack > (min_slack_needed + reserve_wait):
                return ClusterType.NONE
            return ClusterType.ON_DEMAND

        # Spot available: decide between spot and on-demand
        # When slack is very small, prioritize reliability unless switching would itself be too costly.
        if slack <= urgent_slack:
            if last_cluster_type == ClusterType.SPOT:
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND

        # If we are on-demand and spot seems extremely unstable, avoid flip-flopping.
        if last_cluster_type == ClusterType.ON_DEMAND:
            exp_up = self._expected_up_seconds(gap)
            if exp_up < 2.0 * overhead and slack <= (min_slack_needed + 2.0 * reserve_wait):
                return ClusterType.ON_DEMAND

        return ClusterType.SPOT

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
