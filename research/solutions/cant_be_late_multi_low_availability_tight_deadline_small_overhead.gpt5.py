import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_mr_v1"

    def solve(self, spec_path: str) -> "Solution":
        with open(spec_path) as f:
            config = json.load(f)

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)

        # Internal state
        self._last_done_len = 0
        self._done_sum = 0.0
        self.lock_on_demand = False
        self._has_set_region = False
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not self._has_set_region:
            # Stick to initial region to avoid unnecessary restart overhead from switching.
            self._has_set_region = True

        # Efficiently track progress without summing entire list each step
        td_list = self.task_done_time or []
        n = len(td_list)
        if n > self._last_done_len:
            inc_sum = 0.0
            for v in td_list[self._last_done_len : n]:
                inc_sum += v
            self._done_sum += inc_sum
            self._last_done_len = n

        remain = max(0.0, self.task_duration - self._done_sum)
        if remain <= 1e-9:
            return ClusterType.NONE

        # If already on On-Demand, stay to avoid overhead and ensure completion.
        if self.lock_on_demand or last_cluster_type == ClusterType.ON_DEMAND:
            self.lock_on_demand = True
            return ClusterType.ON_DEMAND

        time_left = self.deadline - self.env.elapsed_seconds
        if time_left <= 0:
            self.lock_on_demand = True
            return ClusterType.ON_DEMAND

        gap = float(self.env.gap_seconds)
        overhead = float(self.restart_overhead)

        # Safety margin to handle discrete steps and restart overhead.
        safety_margin = gap + overhead

        # Overhead to switch to OD now (if not already on OD).
        overhead_to_od = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else overhead

        # Commit to OD if we are within the safety window.
        if time_left <= remain + overhead_to_od + safety_margin:
            self.lock_on_demand = True
            return ClusterType.ON_DEMAND

        # Prefer SPOT when available and we have sufficient slack.
        if has_spot:
            return ClusterType.SPOT

        # If SPOT unavailable, decide to wait or switch to OD.
        # Wait one step if we can still safely finish after waiting and switching.
        if time_left - gap > remain + overhead + safety_margin:
            return ClusterType.NONE

        # Otherwise, commit to OD to ensure completion.
        self.lock_on_demand = True
        return ClusterType.ON_DEMAND
