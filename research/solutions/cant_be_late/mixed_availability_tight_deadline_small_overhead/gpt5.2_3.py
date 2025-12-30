import math
from typing import Any

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_v1"

    def __init__(self, args=None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except Exception:
                pass

        self._total_steps = 0
        self._spot_up_steps = 0
        self._prev_has_spot = None
        self._spot_down_transitions = 0

        self._commit_on_demand = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    @staticmethod
    def _done_work_seconds(task_done_time: Any) -> float:
        if not task_done_time:
            return 0.0
        done = 0.0
        try:
            for x in task_done_time:
                if isinstance(x, (int, float)):
                    done += float(x)
                elif isinstance(x, (tuple, list)) and len(x) >= 2:
                    a, b = x[0], x[1]
                    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                        done += max(0.0, float(b) - float(a))
                elif isinstance(x, dict):
                    if "duration" in x and isinstance(x["duration"], (int, float)):
                        done += float(x["duration"])
                    elif "start" in x and "end" in x and isinstance(x["start"], (int, float)) and isinstance(
                        x["end"], (int, float)
                    ):
                        done += max(0.0, float(x["end"]) - float(x["start"]))
        except Exception:
            try:
                done = float(sum(task_done_time))
            except Exception:
                done = 0.0
        return max(0.0, done)

    @staticmethod
    def _wilson_lower_bound(p: float, n: int, z: float) -> float:
        if n <= 0:
            return 0.0
        denom = 1.0 + (z * z) / n
        center = p + (z * z) / (2.0 * n)
        rad = z * math.sqrt(max(0.0, (p * (1.0 - p)) / n + (z * z) / (4.0 * n * n)))
        return max(0.0, (center - rad) / denom)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._total_steps += 1
        if has_spot:
            self._spot_up_steps += 1

        if self._prev_has_spot is not None and self._prev_has_spot and (not has_spot):
            self._spot_down_transitions += 1
        self._prev_has_spot = has_spot

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        restart_overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        done = self._done_work_seconds(getattr(self, "task_done_time", None))
        work_left = max(0.0, task_duration - done)
        time_left = max(0.0, deadline - elapsed)

        if work_left <= 1e-9:
            return ClusterType.NONE

        if time_left <= 1e-9:
            return ClusterType.NONE

        slack_if_od = time_left - work_left

        n = self._total_steps
        p_hat = self._spot_up_steps / n if n > 0 else 0.5
        p_low = self._wilson_lower_bound(p_hat, n, z=1.28) if n > 0 else 0.5

        p_low = min(0.98, max(0.05, p_low))

        denom_t = max(elapsed, max(gap, 1.0))
        trans_rate = self._spot_down_transitions / denom_t
        expected_restarts_remaining = trans_rate * time_left
        expected_overhead_remaining = expected_restarts_remaining * restart_overhead

        overhead_buffer = min(2.0 * 3600.0, 1.5 * expected_overhead_remaining + 2.0 * restart_overhead + max(gap, 0.0))

        commit_slack = max(0.5 * 3600.0, 10.0 * restart_overhead + 2.0 * max(gap, 0.0))
        hard_commit_slack = max(0.15 * 3600.0, 4.0 * restart_overhead + 2.0 * max(gap, 0.0))

        if not self._commit_on_demand:
            if slack_if_od <= hard_commit_slack:
                self._commit_on_demand = True
            else:
                if slack_if_od <= (overhead_buffer + commit_slack) and p_hat < 0.25 and n > 24:
                    self._commit_on_demand = True

        if self._commit_on_demand:
            return ClusterType.ON_DEMAND

        required_fraction = work_left / time_left if time_left > 0 else 1.0
        need_progress_when_no_spot = (work_left + overhead_buffer) > (p_low * time_left)

        if has_spot:
            if last_cluster_type == ClusterType.ON_DEMAND:
                switch_back_slack = max(1.5 * 3600.0, 20.0 * restart_overhead + 3.0 * max(gap, 0.0))
                if slack_if_od <= switch_back_slack:
                    return ClusterType.ON_DEMAND
            return ClusterType.SPOT
        else:
            if need_progress_when_no_spot or required_fraction > (p_low + 0.02):
                return ClusterType.ON_DEMAND
            else:
                return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)