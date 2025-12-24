import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "my_strategy"

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
        self._locked_on_demand = False
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Lock to on-demand if we are already on-demand to avoid flapping
        if not getattr(self, "_locked_on_demand", False):
            if self.env.cluster_type == ClusterType.ON_DEMAND:
                self._locked_on_demand = True

        remaining_work = max(0.0, self.task_duration - sum(self.task_done_time))
        if remaining_work <= 0.0:
            return ClusterType.NONE

        time_left = max(0.0, self.deadline - self.env.elapsed_seconds)
        step = float(self.env.gap_seconds)

        # Overhead to switch to on-demand now (replace any pending overhead)
        overhead_if_switch_now = 0.0 if self._locked_on_demand else self.restart_overhead

        # Conservative guard: allow for worst-case wasted next step (step) when using spot
        must_switch_to_od = (time_left <= (remaining_work + overhead_if_switch_now + step))

        if self._locked_on_demand or must_switch_to_od:
            self._locked_on_demand = True
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        return ClusterType.NONE
