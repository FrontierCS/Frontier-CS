import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "my_strategy"  # REQUIRED: unique identifier

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

        # Internal state for efficient progress tracking and control
        self._my_progress = 0.0
        self._my_last_len = 0
        self._my_committed = False
        self._my_consecutive_no_spot = 0
        return self

    def _update_progress(self) -> None:
        """Incrementally update total work done to avoid O(n^2) summation."""
        td = self.task_done_time
        last_len = self._my_last_len
        if last_len < len(td):
            acc = 0.0
            for i in range(last_len, len(td)):
                acc += td[i]
            self._my_progress += acc
            self._my_last_len = len(td)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.

        Available attributes:
        - self.env.get_current_region(): Get current region index
        - self.env.get_num_regions(): Get total number of regions
        - self.env.switch_region(idx): Switch to region by index
        - self.env.elapsed_seconds: Current time elapsed
        - self.task_duration: Total task duration needed (seconds)
        - self.deadline: Deadline time (seconds)
        - self.restart_overhead: Restart overhead (seconds)
        - self.task_done_time: List of completed work segments
        - self.remaining_restart_overhead: Current pending overhead

        Returns: ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        # Update known progress efficiently
        self._update_progress()

        remaining_work = max(self.task_duration - self._my_progress, 0.0)

        # If work is already completed, do nothing to avoid extra cost
        if remaining_work <= 0.0:
            self._my_committed = True
            return ClusterType.NONE

        time_left = self.deadline - self.env.elapsed_seconds

        # If we're at or past the deadline, always use On-Demand to finish ASAP
        if time_left <= 0.0:
            self._my_committed = True
            return ClusterType.ON_DEMAND

        # Decide when to "commit" to guaranteed On-Demand execution
        if not self._my_committed:
            gap = getattr(self.env, "gap_seconds", 0.0) or 0.0
            # Worst-case time to finish if we switch to On-Demand now
            needed_for_od = remaining_work + self.restart_overhead
            # Safety margin: allow for at least ~2 full steps of slack
            safety_margin = 2.0 * gap
            if time_left <= needed_for_od + safety_margin:
                self._my_committed = True

        # Once committed, always use On-Demand (no region switching to avoid extra overhead)
        if self._my_committed:
            return ClusterType.ON_DEMAND

        # Spot-preferred phase
        if has_spot:
            self._my_consecutive_no_spot = 0
            return ClusterType.SPOT

        # No Spot available and far from deadline: wait to avoid expensive On-Demand
        self._my_consecutive_no_spot += 1
        return ClusterType.NONE
