import math
from typing import Any

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_threshold_v1"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._initialized = False
        self._force_on_demand = False
        self._total_slack = None
        self._cached_done_seconds = 0.0
        self._cached_segments_count = 0

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _initialize(self):
        if self._initialized:
            return
        try:
            deadline = float(self.deadline)
            task_duration = float(self.task_duration)
            self._total_slack = max(deadline - task_duration, 0.0)
        except Exception:
            self._total_slack = None
        self._initialized = True

    def _get_restart_overhead(self) -> float:
        ov = None
        if hasattr(self, "restart_overhead"):
            ov = getattr(self, "restart_overhead")
        if ov is None and hasattr(self, "env") and hasattr(self.env, "restart_overhead"):
            ov = getattr(self.env, "restart_overhead")
        try:
            return float(ov)
        except Exception:
            return 0.0

    def _get_done_seconds(self) -> float:
        tdt = getattr(self, "task_done_time", 0.0)

        if isinstance(tdt, (int, float)):
            return float(tdt)

        try:
            length = len(tdt)
        except Exception:
            try:
                return float(tdt)
            except Exception:
                return 0.0

        if length > self._cached_segments_count:
            for idx in range(self._cached_segments_count, length):
                seg = tdt[idx]
                try:
                    if isinstance(seg, (tuple, list)) and len(seg) >= 2:
                        self._cached_done_seconds += float(seg[1]) - float(seg[0])
                    else:
                        self._cached_done_seconds += float(seg)
                except Exception:
                    try:
                        self._cached_done_seconds += float(seg)
                    except Exception:
                        pass
            self._cached_segments_count = length

        return self._cached_done_seconds

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._initialize()

        env = self.env
        elapsed = float(getattr(env, "elapsed_seconds", 0.0))
        gap = float(getattr(env, "gap_seconds", 0.0))
        deadline = float(self.deadline)
        task_duration = float(self.task_duration)

        done_seconds = self._get_done_seconds()
        remaining_work = max(task_duration - done_seconds, 0.0)

        if remaining_work <= 0.0:
            return ClusterType.NONE

        time_left = max(deadline - elapsed, 0.0)
        slack = time_left - remaining_work

        restart_ov = self._get_restart_overhead()

        spot_risk_slack = 3.0 * restart_ov + 2.0 * gap

        total_slack = self._total_slack
        if total_slack is None:
            total_slack = max(deadline - task_duration, 0.0)
        if total_slack <= 0.0:
            wait_budget = 0.0
        else:
            wait_budget = 0.5 * total_slack
        wait_slack_threshold = spot_risk_slack + wait_budget

        if slack <= 0.0:
            self._force_on_demand = True
        if time_left <= remaining_work + restart_ov:
            self._force_on_demand = True
        if slack <= spot_risk_slack:
            self._force_on_demand = True

        if self._force_on_demand:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        if slack > wait_slack_threshold:
            return ClusterType.NONE

        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
