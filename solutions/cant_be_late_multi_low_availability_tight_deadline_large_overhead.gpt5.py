import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "deadline_guard_v1"

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

        # Internal state for efficient progress tracking
        self._work_done = 0.0
        self._processed_len = 0

        # Control flags
        self._committed_od = False  # Once True, stay on On-Demand until finish

        # Guard time to buffer discretization and overhead uncertainties
        self._gap = float(self.env.gap_seconds)
        self._guard_time = self._gap + float(self.restart_overhead)

        return self

    def _update_work_done_cache(self):
        # Efficient incremental sum of task_done_time
        tdt = self.task_done_time
        n = len(tdt)
        if n > self._processed_len:
            for i in range(self._processed_len, n):
                self._work_done += tdt[i]
            self._processed_len = n

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._update_work_done_cache()

        # Quick exits if already done or no time
        remaining_work = max(self.task_duration - self._work_done, 0.0)
        time_remaining = max(self.deadline - self.env.elapsed_seconds, 0.0)

        if remaining_work <= 0.0 or time_remaining <= 0.0:
            return ClusterType.NONE

        # Threshold for latest safe switch to On-Demand:
        # We assume one restart overhead if we switch to On-Demand later.
        # Guard time ensures safety against discretization and last-moment preemption overhead.
        safe_threshold = remaining_work + self.restart_overhead + self._guard_time

        # If once committed to On-Demand, keep using it
        if self._committed_od:
            return ClusterType.ON_DEMAND

        # If we must start On-Demand now to guarantee finish
        if time_remaining <= safe_threshold:
            self._committed_od = True
            return ClusterType.ON_DEMAND

        # Otherwise, we have slack. Prefer Spot when available.
        if has_spot:
            return ClusterType.SPOT

        # Spot not available: decide to wait or go On-Demand.
        # We can afford to wait one gap if after waiting we still meet the safe threshold.
        if time_remaining - self._gap > safe_threshold:
            return ClusterType.NONE

        # Can't safely wait: commit to On-Demand
        self._committed_od = True
        return ClusterType.ON_DEMAND
