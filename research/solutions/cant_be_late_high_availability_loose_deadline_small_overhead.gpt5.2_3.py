from __future__ import annotations

from collections import deque
from typing import Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_balanced_v1"

    def __init__(self, *args, **kwargs):
        try:
            super().__init__(*args, **kwargs)
        except TypeError:
            try:
                super().__init__()
            except Exception:
                pass

        self._hist: deque[int] = deque()
        self._hist_sum: int = 0
        self._window_len: Optional[int] = None

        self._consec_up: int = 0
        self._consec_down: int = 0

        self._switch_back_k: int = 2
        self._prior_mean: float = 0.70
        self._prior_strength: float = 12.0

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _ensure_window(self) -> None:
        if self._window_len is not None:
            return
        gap = float(getattr(self.env, "gap_seconds", 300.0) or 300.0)
        window_seconds = 6.0 * 3600.0
        self._window_len = max(24, int(window_seconds / max(gap, 1.0)))

    def _update_history(self, has_spot: bool) -> None:
        self._ensure_window()
        v = 1 if has_spot else 0

        if v:
            self._consec_up += 1
            self._consec_down = 0
        else:
            self._consec_down += 1
            self._consec_up = 0

        if self._window_len is None:
            return

        if len(self._hist) >= self._window_len:
            old = self._hist.popleft()
            self._hist_sum -= old
        self._hist.append(v)
        self._hist_sum += v

    def _spot_prob_estimate(self) -> float:
        n = len(self._hist)
        if n <= 0:
            return self._prior_mean
        p = (self._hist_sum + self._prior_strength * self._prior_mean) / (n + self._prior_strength)
        if p < 0.01:
            return 0.01
        if p > 0.99:
            return 0.99
        return p

    def _spot_prob_effective(self) -> float:
        p = self._spot_prob_estimate()
        n = len(self._hist)
        if n <= 1:
            return max(0.05, p - 0.15)
        var = p * (1.0 - p) / max(float(n), 1.0)
        sigma = var ** 0.5
        risk = 1.7 * sigma + 0.02
        return max(0.05, p - risk)

    def _work_done(self) -> float:
        tdt = getattr(self, "task_done_time", None)
        if not tdt:
            return 0.0
        try:
            return float(sum(tdt))
        except Exception:
            s = 0.0
            for x in tdt:
                try:
                    s += float(x)
                except Exception:
                    pass
            return s

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._update_history(has_spot)

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        gap = float(getattr(self.env, "gap_seconds", 300.0) or 300.0)

        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        restart_overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        time_left = deadline - elapsed
        done = self._work_done()
        remaining_work = task_duration - done
        if remaining_work <= 1e-6:
            return ClusterType.NONE

        if time_left <= 0.0:
            return ClusterType.ON_DEMAND

        slack = time_left - remaining_work

        buffer_seconds = max(6.0 * gap, 8.0 * restart_overhead, 900.0)
        commit_slack = max(2.0 * buffer_seconds, 3600.0)
        switch_back_slack = max(buffer_seconds, 3600.0)

        if slack <= commit_slack:
            desired = ClusterType.ON_DEMAND
        else:
            p_eff = self._spot_prob_effective()
            req_wait = remaining_work / max(p_eff, 0.05) + buffer_seconds
            if req_wait <= time_left:
                desired = ClusterType.SPOT if has_spot else ClusterType.NONE
            else:
                desired = ClusterType.SPOT if has_spot else ClusterType.ON_DEMAND

        if desired == ClusterType.SPOT and not has_spot:
            desired = ClusterType.ON_DEMAND

        if desired == ClusterType.SPOT and last_cluster_type == ClusterType.ON_DEMAND:
            if slack < switch_back_slack or self._consec_up < self._switch_back_k:
                desired = ClusterType.ON_DEMAND

        if desired == ClusterType.NONE and slack < buffer_seconds:
            desired = ClusterType.SPOT if has_spot else ClusterType.ON_DEMAND

        if desired == ClusterType.SPOT and not has_spot:
            desired = ClusterType.ON_DEMAND

        return desired

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)