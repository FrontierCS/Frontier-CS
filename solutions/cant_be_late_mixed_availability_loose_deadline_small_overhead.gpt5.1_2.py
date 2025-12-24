from typing import Any

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_smart_v1"

    def __init__(self, args: Any = None):
        super().__init__(args)
        self._policy_inited = False
        self._force_on_demand = False
        self._slack_high = 0.0
        self._slack_mid = 0.0
        self._slack_low = 0.0

    def solve(self, spec_path: str) -> "Solution":
        # Optional: load configuration from spec_path if desired.
        return self

    def _init_policy_params(self) -> None:
        if self._policy_inited:
            return
        try:
            deadline = float(self.deadline)
            task_duration = float(self.task_duration)
            restart_overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        except Exception:
            deadline = 0.0
            task_duration = 0.0
            restart_overhead = 0.0

        initial_slack = max(0.0, deadline - task_duration - restart_overhead)

        # Thresholds are fractions of initial slack, but never too small
        high = max(4.0 * restart_overhead, 0.5 * initial_slack)
        mid = max(3.0 * restart_overhead, 0.25 * initial_slack)
        low = max(2.0 * restart_overhead, 0.10 * initial_slack)

        # Enforce ordering: high > mid > low
        if high <= mid:
            high = mid + restart_overhead
        if mid <= low:
            mid = low + restart_overhead

        self._slack_high = high
        self._slack_mid = mid
        self._slack_low = low
        self._policy_inited = True

    def _compute_completed_time(self) -> float:
        segments = getattr(self, "task_done_time", None)
        if not segments:
            return 0.0
        total = 0.0
        for seg in segments:
            try:
                if isinstance(seg, (list, tuple)):
                    if len(seg) >= 2:
                        s = float(seg[0])
                        e = float(seg[1])
                        total += max(0.0, e - s)
                    elif len(seg) == 1:
                        total += float(seg[0])
                else:
                    total += float(seg)
            except Exception:
                continue
        return total

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._init_policy_params()

        # Basic environment values
        t = float(self.env.elapsed_seconds)
        deadline = float(self.deadline)
        time_left = deadline - t

        if time_left <= 0.0:
            return ClusterType.NONE

        done = self._compute_completed_time()
        remaining = max(0.0, float(self.task_duration) - done)
        if remaining <= 0.0:
            return ClusterType.NONE

        current_type = self.env.cluster_type if hasattr(self, "env") else last_cluster_type
        if current_type == ClusterType.ON_DEMAND:
            overhead_if_switch_to_od = 0.0
        else:
            overhead_if_switch_to_od = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        minimal_time_needed = remaining + overhead_if_switch_to_od
        extra_slack = time_left - minimal_time_needed

        # Once we decide to lock into on-demand, never go back to spot.
        if self._force_on_demand:
            return ClusterType.ON_DEMAND

        # If slack is very tight, force on-demand and lock in.
        if extra_slack <= self._slack_low:
            self._force_on_demand = True
            return ClusterType.ON_DEMAND

        # Moderate slack: never idle. Use spot when available, OD otherwise.
        if extra_slack <= self._slack_mid:
            if has_spot:
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND

        # High slack: prefer spot, idle when not available to save cost.
        if has_spot:
            return ClusterType.SPOT
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
