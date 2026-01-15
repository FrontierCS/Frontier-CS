import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_multiregion_v1"

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
        self._init_custom_state()
        return self

    def _init_custom_state(self) -> None:
        self._initialized_state = False
        self._work_done = 0.0
        self._last_task_index = 0
        self._safety_margin = None
        self._on_demand_committed = False

        task_duration = getattr(self, "task_duration", 0.0)
        if isinstance(task_duration, (list, tuple)):
            self._task_duration_total = float(task_duration[0]) if task_duration else 0.0
        else:
            self._task_duration_total = float(task_duration)

        restart_overhead = getattr(self, "restart_overhead", 0.0)
        if isinstance(restart_overhead, (list, tuple)):
            self._restart_overhead_total = float(restart_overhead[0]) if restart_overhead else 0.0
        else:
            self._restart_overhead_total = float(restart_overhead)

    def _update_safety_margin_if_needed(self) -> None:
        if self._safety_margin is not None:
            return
        gap = getattr(self.env, "gap_seconds", 0.0)
        ro = self._restart_overhead_total
        margin = 4.0 * (ro + gap)
        max_margin = 0.1 * self._task_duration_total if self._task_duration_total > 0.0 else margin
        if margin > max_margin:
            margin = max_margin
        min_margin = 2.0 * gap
        if margin < min_margin:
            margin = min_margin
        self._safety_margin = margin

    def _update_work_done_cache(self) -> None:
        if not self._initialized_state:
            total = 0.0
            for v in self.task_done_time:
                total += v
            self._work_done = total
            self._last_task_index = len(self.task_done_time)
            self._initialized_state = True
        else:
            n = len(self.task_done_time)
            if n > self._last_task_index:
                added = 0.0
                for i in range(self._last_task_index, n):
                    added += self.task_done_time[i]
                self._work_done += added
                self._last_task_index = n

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not hasattr(self, "_initialized_state"):
            self._init_custom_state()

        self._update_safety_margin_if_needed()
        self._update_work_done_cache()

        remaining_work = self._task_duration_total - self._work_done
        if remaining_work <= 0.0:
            return ClusterType.NONE

        if self._on_demand_committed:
            return ClusterType.ON_DEMAND

        current_time = getattr(self.env, "elapsed_seconds", 0.0)
        deadline = getattr(self, "deadline", None)
        if deadline is None:
            if has_spot:
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND

        time_left = deadline - current_time

        if time_left <= 0.0:
            self._on_demand_committed = True
            return ClusterType.ON_DEMAND

        if last_cluster_type is ClusterType.ON_DEMAND:
            self._on_demand_committed = True
            return ClusterType.ON_DEMAND

        overhead_if_switch = self._restart_overhead_total
        time_needed_on_demand = overhead_if_switch + max(0.0, remaining_work)
        slack = time_left - time_needed_on_demand

        if slack <= self._safety_margin:
            self._on_demand_committed = True
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        return ClusterType.NONE