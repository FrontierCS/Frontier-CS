import json
import math
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_mr_sched"

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
        self._committed_od = False
        self._last_done_len = 0
        self._work_done_sum = 0.0
        return self

    def _time_on_demand(self, remaining_work: float, overhead: float) -> float:
        # Minimal elapsed time to finish when using only on-demand, starting now,
        # paying the given overhead exactly once at the beginning.
        gap = self.env.gap_seconds
        need = max(0.0, remaining_work)
        # Number of steps required accounting for initial overhead lost from first step's credit.
        steps = int(math.ceil((need + overhead) / gap))
        return steps * gap + overhead

    def _update_work_done_cache(self):
        # Maintain a running sum to avoid summing an ever-growing list each step
        l = len(self.task_done_time)
        if l != self._last_done_len:
            if l > self._last_done_len:
                for i in range(self._last_done_len, l):
                    self._work_done_sum += self.task_done_time[i]
            else:
                # Fallback if list was reset for any reason
                self._work_done_sum = sum(self.task_done_time)
            self._last_done_len = l

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If we already committed to on-demand, never leave it.
        if self._committed_od or last_cluster_type == ClusterType.ON_DEMAND:
            self._committed_od = True
            return ClusterType.ON_DEMAND

        self._update_work_done_cache()

        gap = self.env.gap_seconds
        elapsed = self.env.elapsed_seconds
        deadline = self.deadline
        restart_overhead = self.restart_overhead

        remaining_work = max(0.0, self.task_duration - self._work_done_sum)
        if remaining_work <= 0.0:
            return ClusterType.NONE

        time_remaining = deadline - elapsed

        # If we're somehow out of time, best effort: go on-demand.
        if time_remaining <= 0.0:
            self._committed_od = True
            return ClusterType.ON_DEMAND

        # Decision logic:
        # - If spot is available, check if taking one spot step (including possible overhead)
        #   still leaves enough time to finish by switching to on-demand afterwards.
        # - If spot is not available, check if we can afford to wait one NONE step,
        #   and still finish via on-demand afterwards.
        if has_spot:
            # Determine the overhead for taking a SPOT step now.
            # If last was SPOT, continuing SPOT incurs no new overhead; otherwise pay restart_overhead now.
            if last_cluster_type == ClusterType.SPOT:
                spot_step_overhead = 0.0
            else:
                spot_step_overhead = restart_overhead

            # Progress and time after taking one SPOT step now
            progress_spot = max(0.0, gap - spot_step_overhead)
            remaining_after_spot = max(0.0, remaining_work - progress_spot)
            time_after_spot = time_remaining - (gap + spot_step_overhead)

            # Time required if we switch to ON_DEMAND after this SPOT step
            od_time_after = self._time_on_demand(remaining_after_spot, restart_overhead)

            if time_after_spot >= od_time_after:
                return ClusterType.SPOT
            else:
                # Not safe to take another SPOT step; commit to ON_DEMAND now
                self._committed_od = True
                return ClusterType.ON_DEMAND
        else:
            # No spot available: can we afford to wait one step doing nothing?
            time_after_none = time_remaining - gap
            od_time_after = self._time_on_demand(remaining_work, restart_overhead)

            if time_after_none >= od_time_after:
                return ClusterType.NONE
            else:
                # Must commit to ON_DEMAND now to guarantee completion
                self._committed_od = True
                return ClusterType.ON_DEMAND