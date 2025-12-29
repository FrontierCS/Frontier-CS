import argparse
from typing import Any, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_jit_v1"

    def __init__(self, args: Optional[argparse.Namespace] = None):
        try:
            super().__init__(args)
        except Exception:
            pass
        self.args = args

        self._locked_od = False

        self._done_sum = 0.0
        self._done_len = 0

        self._prev_has_spot: Optional[bool] = None
        self._spot_streak = 0.0
        self._no_spot_streak = 0.0

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _get_done_work(self) -> float:
        tdt = getattr(self, "task_done_time", None)
        if not isinstance(tdt, list):
            return 0.0
        n = len(tdt)
        if n == self._done_len:
            return self._done_sum
        if n > self._done_len:
            s = self._done_sum
            for i in range(self._done_len, n):
                try:
                    s += float(tdt[i])
                except Exception:
                    pass
            self._done_sum = s
            self._done_len = n
            return s
        # List was reset/shrunk; recompute
        s = 0.0
        for x in tdt:
            try:
                s += float(x)
            except Exception:
                pass
        self._done_sum = s
        self._done_len = n
        return s

    def _update_streaks(self, has_spot: bool, gap: float) -> None:
        if self._prev_has_spot is None:
            self._prev_has_spot = has_spot
        if has_spot:
            if self._prev_has_spot is True:
                self._spot_streak += gap
            else:
                self._spot_streak = gap
            self._no_spot_streak = 0.0
        else:
            if self._prev_has_spot is False:
                self._no_spot_streak += gap
            else:
                self._no_spot_streak = gap
            self._spot_streak = 0.0
        self._prev_has_spot = has_spot

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        env = getattr(self, "env", None)
        if env is None:
            return ClusterType.ON_DEMAND if not has_spot else ClusterType.SPOT

        elapsed = float(getattr(env, "elapsed_seconds", 0.0) or 0.0)
        gap = float(getattr(env, "gap_seconds", 0.0) or 0.0)
        if gap <= 0:
            gap = 60.0

        self._update_streaks(has_spot, gap)

        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        restart_overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        done = self._get_done_work()
        remaining_work = task_duration - done
        if remaining_work <= 0:
            self._locked_od = False
            return ClusterType.NONE

        remaining_time = deadline - elapsed
        if remaining_time <= 0:
            self._locked_od = True
            return ClusterType.ON_DEMAND

        # Conservative time safety buffer to account for step discretization + at least one restart risk
        start_overhead = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else restart_overhead
        risk_buffer = restart_overhead if has_spot else 0.0
        safety = start_overhead + risk_buffer + 2.0 * gap

        # If we're close enough that any delay could jeopardize the deadline, lock to on-demand.
        if self._locked_od or (remaining_time <= remaining_work + safety):
            self._locked_od = True
            return ClusterType.ON_DEMAND

        # Not locked: use spot whenever available, otherwise wait (NONE) to maximize spot usage.
        if has_spot:
            return ClusterType.SPOT
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)