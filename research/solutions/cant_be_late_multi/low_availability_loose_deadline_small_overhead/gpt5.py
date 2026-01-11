import json
from argparse import Namespace
from math import ceil

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

        self._accumulated_work = 0.0
        self._last_task_done_len = 0
        self._committed_to_od = False
        return self

    def _update_progress_cache(self):
        new_len = len(self.task_done_time)
        if new_len > self._last_task_done_len:
            # Sum only new segments to keep per-step O(1) amortized
            delta = 0.0
            for i in range(self._last_task_done_len, new_len):
                delta += self.task_done_time[i]
            self._accumulated_work += delta
            self._last_task_done_len = new_len

    def _required_time_on_od_seconds(self, remaining_work: float) -> float:
        # Compute minimal wall-clock time (in seconds) to finish remaining_work on OD starting now,
        # accounting for restart overhead and step discretization.
        gap = getattr(self.env, "gap_seconds", 1.0)
        if gap <= 0:
            gap = 1.0

        # Overhead to pay from now if we choose OD:
        # - If currently on OD, only remaining_restart_overhead is relevant.
        # - Otherwise, full restart_overhead applies.
        try:
            current_cluster = self.env.cluster_type
        except Exception:
            current_cluster = None

        try:
            remaining_overhead = float(self.remaining_restart_overhead)
        except Exception:
            remaining_overhead = 0.0

        if current_cluster == ClusterType.ON_DEMAND:
            overhead_to_pay = max(0.0, remaining_overhead)
        else:
            overhead_to_pay = self.restart_overhead

        # Steps needed so that total progress gap*steps - overhead_to_pay >= remaining_work
        steps_needed = ceil((remaining_work + overhead_to_pay) / gap - 1e-12)
        if steps_needed < 0:
            steps_needed = 0
        return steps_needed * gap

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update progress cache
        self._update_progress_cache()

        # If already done, do nothing
        remaining_work = max(0.0, self.task_duration - self._accumulated_work)
        if remaining_work <= 0.0:
            return ClusterType.NONE

        time_left = self.deadline - self.env.elapsed_seconds
        if time_left <= 0.0:
            # Out of time; return NONE to avoid further costs (penalty handled by env)
            return ClusterType.NONE

        # If not yet committed, check if we must switch to OD to guarantee finishing
        if not self._committed_to_od:
            required_time_od = self._required_time_on_od_seconds(remaining_work)
            if time_left <= required_time_od + 1e-9:
                self._committed_to_od = True

        # Action selection
        if self._committed_to_od:
            return ClusterType.ON_DEMAND

        # Prefer SPOT when available; otherwise, wait
        if has_spot:
            return ClusterType.SPOT

        # No spot; wait to save cost until commitment threshold triggers
        return ClusterType.NONE