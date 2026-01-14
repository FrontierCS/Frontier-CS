import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy focusing on deadline safety and low cost."""

    NAME = "my_strategy"

    def __init__(self):
        # Delay MultiRegionStrategy initialization until solve() when spec is available.
        self._committed_on_demand = False
        self._done_so_far = 0.0
        self._last_task_done_len = 0

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the solution from spec_path config.

        The spec file contains:
        - deadline: deadline in hours
        - duration: task duration in hours
        - overhead: restart overhead in hours
        - trace_files: list of trace file paths (one per region)
        """
        with open(spec_path) as f:
            config = json.load(f)

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)

        # Initialize tracking of accumulated work.
        self._committed_on_demand = False
        self._done_so_far = 0.0
        self._last_task_done_len = 0
        if hasattr(self, "task_done_time") and self.task_done_time:
            self._done_so_far = sum(self.task_done_time)
            self._last_task_done_len = len(self.task_done_time)

        return self

    def _update_progress(self) -> None:
        """Incrementally track total completed work to avoid O(n) summation each step."""
        if not hasattr(self, "task_done_time"):
            return
        curr_len = len(self.task_done_time)
        if curr_len > self._last_task_done_len:
            new_segments = self.task_done_time[self._last_task_done_len:curr_len]
            total = self._done_so_far
            for seg in new_segments:
                total += seg
            self._done_so_far = total
            self._last_task_done_len = curr_len

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.

        Returns: ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        # Update accumulated work efficiently.
        self._update_progress()

        remaining_work = self.task_duration - self._done_so_far
        if remaining_work <= 0:
            # Task already completed.
            return ClusterType.NONE

        time_left = self.deadline - self.env.elapsed_seconds
        if time_left <= 0:
            # Past deadline; nothing more can help.
            return ClusterType.NONE

        gap = self.env.gap_seconds
        # Conservative safety margin: one full risky step (gap) plus up to
        # two restart overheads (one from a late Spot/preemption event and one
        # when switching to On-Demand).
        safety_margin = 2.0 * self.restart_overhead + gap

        if not self._committed_on_demand:
            # If we no longer have enough time to risk another non-On-Demand step,
            # permanently commit to On-Demand now.
            if time_left < remaining_work + safety_margin:
                self._committed_on_demand = True

        if self._committed_on_demand:
            # From now on, always run on reliable On-Demand instances.
            return ClusterType.ON_DEMAND

        # Pre-commit phase: aggressively use Spot; otherwise wait (NONE) to save cost.
        if has_spot:
            return ClusterType.SPOT

        return ClusterType.NONE