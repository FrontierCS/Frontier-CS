import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy with deadline guarantee."""
    NAME = "cant_be_late_threshold_v1"

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

        # Internal tracking of progress to avoid O(n) sum every step.
        self._progress_done = 0.0
        self._last_seg_index = 0
        self.committed_to_ondemand = False

        return self

    def _update_progress(self) -> None:
        """Incrementally update total work done from task_done_time list."""
        td_list = self.task_done_time
        l = len(td_list)
        if l > self._last_seg_index:
            s = 0.0
            for i in range(self._last_seg_index, l):
                s += td_list[i]
            self._progress_done += s
            self._last_seg_index = l

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Lazy init in case solve() was not called for some reason.
        if not hasattr(self, "_progress_done"):
            self._progress_done = 0.0
            self._last_seg_index = 0
            self.committed_to_ondemand = False

        # Update completed work.
        self._update_progress()

        remaining_work = self.task_duration - self._progress_done
        if remaining_work <= 0.0:
            # Task already finished; no need to run anymore.
            return ClusterType.NONE

        elapsed = self.env.elapsed_seconds
        remaining_time = self.deadline - elapsed

        if remaining_time <= 0.0:
            # Deadline already missed; run cheapest available to eventually finish.
            if has_spot:
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND

        # Time step length.
        dt = self.env.gap_seconds
        if dt <= 0.0:
            dt = 1.0  # Fallback to positive value for safety.

        # Commit-to-On-Demand decision to guarantee meeting deadline.
        # Ensure that even if we waited one more step, we would still have
        # enough time to run purely on On-Demand (once started).
        threshold_time = self.restart_overhead + remaining_work + dt
        if (not self.committed_to_ondemand) and remaining_time <= threshold_time:
            self.committed_to_ondemand = True

        if self.committed_to_ondemand:
            return ClusterType.ON_DEMAND

        # Pre-commit phase: use Spot when available, otherwise wait (NONE).
        if has_spot:
            return ClusterType.SPOT
        return ClusterType.NONE
