import json
from argparse import Namespace
from math import ceil

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
        self._od_committed = False
        return self

    def _remaining_work(self) -> float:
        done = sum(self.task_done_time)
        remaining = self.task_duration - done
        return max(remaining, 0.0)

    def _steps_needed(self, remaining_work: float, overhead: float) -> int:
        g = self.env.gap_seconds
        # Use a tiny epsilon to avoid floating point rounding increasing steps unnecessarily
        eps = 1e-12
        v = (max(remaining_work, 0.0) + max(overhead, 0.0)) / g
        return int(ceil(v - eps))

    def _time_needed_on_demand(self, remaining_work: float, overhead: float) -> float:
        steps = self._steps_needed(remaining_work, overhead)
        return steps * self.env.gap_seconds

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        g = self.env.gap_seconds
        now = self.env.elapsed_seconds
        time_left = self.deadline - now
        remaining_work = self._remaining_work()

        # If already finished, do nothing
        if remaining_work <= 0.0:
            return ClusterType.NONE

        # Once we commit to on-demand, never switch back (avoid restart penalties and deadline risk)
        if self._od_committed or last_cluster_type == ClusterType.ON_DEMAND:
            self._od_committed = True
            return ClusterType.ON_DEMAND

        # Safety epsilon for comparisons
        eps = 1e-9

        # Time to finish if we commit to on-demand now (we are not currently on-demand)
        T_od_now = self._time_needed_on_demand(remaining_work, self.restart_overhead)

        # If we're at or past the last safe moment, commit to on-demand now
        if time_left <= T_od_now + eps:
            self._od_committed = True
            return ClusterType.ON_DEMAND

        # Check if it's safe to delay one step with zero progress and still finish by switching to OD next step
        # Worst case for this next step is zero useful work
        T_od_if_commit_next = T_od_now  # same remaining work, same overhead
        safe_to_delay_one_step = time_left > (g + T_od_if_commit_next + eps)

        if safe_to_delay_one_step:
            if has_spot:
                return ClusterType.SPOT
            else:
                # Wait for spot if we still have safe slack
                return ClusterType.NONE

        # Not safe to delay; commit to on-demand now
        self._od_committed = True
        return ClusterType.ON_DEMAND
