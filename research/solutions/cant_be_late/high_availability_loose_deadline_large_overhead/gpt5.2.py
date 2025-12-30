import argparse
from typing import Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cbl_safe_spot_v1"

    def __init__(self, args: Optional[argparse.Namespace] = None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except Exception:
                pass

        self._last_elapsed = None

        self._commit_od = False

        self._p_spot = 0.70
        self._p_alpha = 0.03

        self._down_run_steps = 0
        self._mean_down_seconds = 1800.0
        self._down_beta = 0.20

        self._done_sum = 0.0
        self._done_len = 0

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _reset_episode_state(self):
        self._commit_od = False

        self._p_spot = 0.70
        self._down_run_steps = 0
        self._mean_down_seconds = 1800.0

        self._done_sum = 0.0
        self._done_len = 0

    def _update_progress_cache(self):
        tdt = getattr(self, "task_done_time", None)
        if not tdt:
            self._done_sum = 0.0
            self._done_len = 0
            return

        n = len(tdt)
        if n < self._done_len:
            self._done_sum = 0.0
            self._done_len = 0

        if n > self._done_len:
            self._done_sum += float(sum(tdt[self._done_len:]))
            self._done_len = n

    def _compute_buffer_seconds(self, gap: float) -> float:
        ro = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        base = 2.0 * gap + 0.5 * ro

        down_buf = 2.0 * max(0.0, float(self._mean_down_seconds))
        down_buf = min(down_buf, 6.0 * 3600.0)

        p = float(self._p_spot)
        extra = 0.0
        if p < 0.55:
            extra += 3600.0
        if p < 0.45:
            extra += 3600.0
        if p < 0.35:
            extra += 3600.0

        buf = base + down_buf + extra
        buf = max(buf, 3600.0)
        return buf

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        gap = float(getattr(self.env, "gap_seconds", 60.0) or 60.0)

        if self._last_elapsed is None:
            self._last_elapsed = elapsed
        elif elapsed + 1e-9 < self._last_elapsed:
            self._reset_episode_state()
            self._last_elapsed = elapsed
        else:
            self._last_elapsed = elapsed

        hs = 1.0 if has_spot else 0.0
        self._p_spot = (1.0 - self._p_alpha) * self._p_spot + self._p_alpha * hs
        self._p_spot = min(0.999, max(0.001, self._p_spot))

        if has_spot:
            if self._down_run_steps > 0:
                down_seconds = self._down_run_steps * gap
                self._mean_down_seconds = (1.0 - self._down_beta) * self._mean_down_seconds + self._down_beta * down_seconds
                self._down_run_steps = 0
        else:
            self._down_run_steps += 1

        self._update_progress_cache()
        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        remaining_work = max(0.0, task_duration - float(self._done_sum))

        if remaining_work <= 0.0:
            return ClusterType.NONE

        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        remaining_time = deadline - elapsed

        if last_cluster_type == ClusterType.ON_DEMAND:
            self._commit_od = True

        overhead_to_od = 0.0
        ro = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        if last_cluster_type != ClusterType.ON_DEMAND:
            overhead_to_od = ro

        buffer_seconds = self._compute_buffer_seconds(gap)
        if remaining_time <= remaining_work + overhead_to_od + buffer_seconds:
            self._commit_od = True

        if self._commit_od:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)