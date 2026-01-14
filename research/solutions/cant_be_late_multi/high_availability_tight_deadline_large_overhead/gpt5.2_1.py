import json
from argparse import Namespace
from typing import Optional

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_v1"

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

        self._on_demand_started = False
        self._done_sum = 0.0
        self._done_len = 0
        self._none_type = getattr(ClusterType, "NONE", getattr(ClusterType, "None"))
        self._spot_type = getattr(ClusterType, "SPOT")
        self._od_type = getattr(ClusterType, "ON_DEMAND")
        self._eps = 1e-9
        return self

    def _update_done(self) -> float:
        tdt = self.task_done_time
        l = len(tdt)
        if l > self._done_len:
            self._done_sum += sum(tdt[self._done_len : l])
            self._done_len = l
        return self._done_sum

    def _can_wait_one_step_and_still_finish_with_ondemand(self, remaining_work: float, time_left: float) -> bool:
        gap = float(self.env.gap_seconds)
        # If we wait this step, next step we'd (re)start on-demand, costing one restart overhead.
        return (time_left - gap) + self._eps >= (remaining_work + float(self.restart_overhead))

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        done = self._update_done()
        remaining_work = float(self.task_duration) - float(done)
        if remaining_work <= self._eps:
            return self._none_type

        if last_cluster_type == self._od_type:
            self._on_demand_started = True

        if self._on_demand_started:
            return self._od_type

        time_left = float(self.deadline) - float(self.env.elapsed_seconds)

        if has_spot:
            return self._spot_type

        if self._can_wait_one_step_and_still_finish_with_ondemand(remaining_work, time_left):
            return self._none_type

        self._on_demand_started = True
        return self._od_type