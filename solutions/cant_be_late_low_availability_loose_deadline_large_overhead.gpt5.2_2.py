import math
import os
import json
from typing import Any, Optional

try:
    from sky_spot.strategies.strategy import Strategy
    from sky_spot.utils import ClusterType
except Exception:
    from enum import Enum

    class ClusterType(Enum):
        SPOT = "spot"
        ON_DEMAND = "on_demand"
        NONE = "none"

    class Strategy:
        def __init__(self, *args, **kwargs):
            self.env = type("Env", (), {"elapsed_seconds": 0.0, "gap_seconds": 300.0, "cluster_type": ClusterType.NONE})()
            self.task_duration = 0.0
            self.task_done_time = []
            self.deadline = 0.0
            self.restart_overhead = 0.0


class Solution(Strategy):
    NAME = "cant_be_late_v1"

    def __init__(self, args: Optional[Any] = None):
        try:
            super().__init__(args)
        except Exception:
            try:
                super().__init__()
            except Exception:
                pass
        self.args = args
        self._reset_state()

    def _reset_state(self):
        self._initialized = False
        self._committed_od = False

        self._prev_has_spot = None
        self._consec_spot_avail = 0
        self._consec_spot_unavail = 0

        self._total_steps = 0
        self._spot_steps = 0

        self._cur_on_streak = 0
        self._on_streak_sum = 0
        self._on_streak_cnt = 0

        self._cached_done = 0.0
        self._cached_td_len = -1

        self._prev_done_obs = None

        self._od_guard = 0.0
        self._spot_risk_budget = 0.0
        self._idle_slack_threshold = 0.0
        self._late_stage_slack = 0.0
        self._min_remaining_to_switch_spot = 0.0
        self._switch_from_od_slack = 0.0

    def solve(self, spec_path: str) -> "Solution":
        self._reset_state()
        if spec_path and os.path.exists(spec_path):
            try:
                with open(spec_path, "r") as f:
                    _ = json.load(f)
            except Exception:
                pass
        return self

    def _ensure_initialized(self):
        if self._initialized:
            return
        gap = float(getattr(self.env, "gap_seconds", 300.0) or 300.0)
        ro = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        td = float(getattr(self, "task_duration", 0.0) or 0.0)

        self._od_guard = max(ro + gap, 2.0 * gap)
        self._spot_risk_budget = max(2.5 * ro, 3.0 * gap)
        self._idle_slack_threshold = self._od_guard + max(0.5 * ro, 1.0 * gap)
        self._late_stage_slack = max(2.0 * ro, 3.0 * gap)
        self._min_remaining_to_switch_spot = max(2.0 * ro, 2.0 * gap)
        self._switch_from_od_slack = max(4.0 * ro, 12.0 * gap, 3600.0, 0.01 * td)

        self._initialized = True

    def _get_work_done(self) -> float:
        td = getattr(self, "task_done_time", None)
        if td is None:
            return 0.0
        if isinstance(td, (int, float)):
            return float(td)
        if isinstance(td, (list, tuple)):
            l = len(td)
            if l == 0:
                self._cached_done = 0.0
                self._cached_td_len = 0
                return 0.0
            if self._cached_td_len == -1:
                s = float(sum(float(x) for x in td))
                self._cached_done = s
                self._cached_td_len = l
                return s
            if l == self._cached_td_len:
                return float(self._cached_done)
            if l > self._cached_td_len:
                try:
                    add = float(sum(float(x) for x in td[self._cached_td_len :]))
                    self._cached_done = float(self._cached_done) + add
                    self._cached_td_len = l
                    return float(self._cached_done)
                except Exception:
                    s = float(sum(float(x) for x in td))
                    self._cached_done = s
                    self._cached_td_len = l
                    return s
            s = float(sum(float(x) for x in td))
            self._cached_done = s
            self._cached_td_len = l
            return s
        try:
            return float(td)
        except Exception:
            return 0.0

    def _update_spot_stats(self, has_spot: bool):
        self._total_steps += 1
        if has_spot:
            self._spot_steps += 1

        if self._prev_has_spot is None:
            self._prev_has_spot = has_spot

        if has_spot:
            self._consec_spot_avail = self._consec_spot_avail + 1 if self._prev_has_spot else 1
            self._consec_spot_unavail = 0
            self._cur_on_streak = self._cur_on_streak + 1 if self._prev_has_spot else 1
        else:
            self._consec_spot_unavail = self._consec_spot_unavail + 1 if (self._prev_has_spot is False) else 1
            self._consec_spot_avail = 0
            if self._prev_has_spot:
                self._on_streak_sum += self._cur_on_streak
                self._on_streak_cnt += 1
            self._cur_on_streak = 0

        self._prev_has_spot = has_spot

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_initialized()
        self._update_spot_stats(bool(has_spot))

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        time_left = max(0.0, deadline - elapsed)

        done = self._get_work_done()
        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        remaining = max(0.0, task_duration - done)

        if remaining <= 0.0:
            return ClusterType.NONE

        slack = time_left - remaining

        if time_left <= remaining + self._od_guard:
            self._committed_od = True

        if self._committed_od:
            return ClusterType.ON_DEMAND

        if not has_spot:
            if slack > self._idle_slack_threshold:
                return ClusterType.NONE
            return ClusterType.ON_DEMAND

        if remaining <= self._min_remaining_to_switch_spot:
            return ClusterType.ON_DEMAND

        if slack <= self._spot_risk_budget:
            return ClusterType.ON_DEMAND

        if last_cluster_type == ClusterType.ON_DEMAND and slack <= self._switch_from_od_slack:
            return ClusterType.ON_DEMAND

        return ClusterType.SPOT

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
