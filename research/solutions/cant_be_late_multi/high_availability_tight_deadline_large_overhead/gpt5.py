import json
import math
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
        self._committed_on_demand = False
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not hasattr(self, "_committed_on_demand"):
            self._committed_on_demand = False

        # If already on on-demand, keep running to avoid extra overhead
        if last_cluster_type == ClusterType.ON_DEMAND:
            self._committed_on_demand = True

        # Compute remaining work and time left
        remaining_work = max(0.0, self.task_duration - sum(self.task_done_time))
        if remaining_work <= 0.0:
            return ClusterType.NONE

        time_left = max(0.0, self.deadline - self.env.elapsed_seconds)
        g = self.env.gap_seconds
        o = self.restart_overhead

        # If committed to on-demand, continue
        if self._committed_on_demand:
            return ClusterType.ON_DEMAND

        # Time needed to finish if we start ON_DEMAND now:
        # First step costs gap + overhead time and yields (gap - overhead) progress.
        # Total time = overhead + ceil((remaining_work + overhead) / gap) * gap
        steps_needed = int(math.ceil((remaining_work + o) / g)) if g > 0 else 0
        ondemand_time_needed_now = o + steps_needed * g

        # If delaying one more step could cause missing deadline, start ON_DEMAND now.
        if time_left - g < ondemand_time_needed_now:
            self._committed_on_demand = True
            return ClusterType.ON_DEMAND

        # Otherwise, use Spot when available, else pause to save cost.
        if has_spot:
            return ClusterType.SPOT
        return ClusterType.NONE