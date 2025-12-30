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
        self.consecutive_none = 0
        return self

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
        if has_spot:
            self.consecutive_none = 0
            return ClusterType.SPOT

        current = self.env.get_current_region()
        num = self.env.get_num_regions()
        gap = self.env.gap_seconds

        total_done = sum(self.task_done_time)
        rem_work = self.task_duration - total_done
        rem_time = self.deadline - self.env.elapsed_seconds - self.remaining_restart_overhead
        if rem_time <= 0 or gap <= 0:
            return ClusterType.ON_DEMAND

        approx_steps_rem = rem_time / gap
        approx_work_steps_rem = rem_work / gap

        hurry = (approx_work_steps_rem + 5 > approx_steps_rem)

        if num == 1 or hurry:
            self.consecutive_none = 0
            return ClusterType.ON_DEMAND

        self.consecutive_none += 1
        if self.consecutive_none > num + 5:
            self.consecutive_none = 0
            return ClusterType.ON_DEMAND

        next_r = (current + 1) % num
        self.env.switch_region(next_r)
        return ClusterType.NONE