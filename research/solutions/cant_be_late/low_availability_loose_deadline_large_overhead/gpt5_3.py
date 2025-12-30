from typing import Any
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_spot_guard"

    def __init__(self, args: Any = None):
        super().__init__(args)
        self._committed_od = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _remaining_work(self) -> float:
        done = sum(self.task_done_time) if self.task_done_time else 0.0
        return max(0.0, self.task_duration - done)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If currently on-demand, stick to it to avoid extra overhead or risk.
        if last_cluster_type == ClusterType.ON_DEMAND:
            self._committed_od = True

        remaining_work = self._remaining_work()
        if remaining_work <= 0.0:
            return ClusterType.NONE

        time_left = self.deadline - self.env.elapsed_seconds
        if time_left <= 0.0:
            # Best effort: choose on-demand
            self._committed_od = True
            return ClusterType.ON_DEMAND

        gap = self.env.gap_seconds
        overhead = self.restart_overhead
        safety_margin = max(gap * 2.0, 60.0)

        if self._committed_od:
            return ClusterType.ON_DEMAND

        # Compute whether we must commit to OD now to meet deadline.
        od_overhead_if_switch_now = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else overhead
        must_commit_od = time_left <= (remaining_work + od_overhead_if_switch_now + safety_margin)
        if must_commit_od:
            self._committed_od = True
            return ClusterType.ON_DEMAND

        # Prefer SPOT if available and safe.
        if has_spot:
            # If we are already on SPOT, no new overhead to continue.
            start_spot_overhead_now = 0.0 if last_cluster_type == ClusterType.SPOT else overhead
            # Ensure we have slack to pay potential SPOT overhead now and still fall back to OD later if needed.
            safe_to_start_spot = time_left > (remaining_work + overhead + start_spot_overhead_now + safety_margin)
            if safe_to_start_spot:
                return ClusterType.SPOT
            else:
                # Not safe to start SPOT. Decide whether to wait a step or commit to OD now.
                # Safe to wait one step if after waiting we still can finish with OD (including OD overhead).
                will_be_safe_after_wait = (time_left - gap) > (remaining_work + overhead + safety_margin)
                if will_be_safe_after_wait:
                    return ClusterType.NONE
                else:
                    self._committed_od = True
                    return ClusterType.ON_DEMAND

        # Spot unavailable: consider waiting if safe; else commit to OD.
        will_be_safe_after_wait = (time_left - gap) > (remaining_work + overhead + safety_margin)
        if will_be_safe_after_wait:
            return ClusterType.NONE
        else:
            self._committed_od = True
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)