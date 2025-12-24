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
        self.consecutive_no_spot = 0
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
        # Your decision logic here
        total_done = sum(self.task_done_time)
        rem_work = self.task_duration - total_done
        rem_wall = self.deadline - self.env.elapsed_seconds
        pending_overhead = getattr(self, 'remaining_restart_overhead', 0.0)
        effective_rem_time = rem_wall - pending_overhead
        is_tight = rem_work > effective_rem_time * 0.95

        if has_spot:
            self.consecutive_no_spot = 0
            return ClusterType.SPOT

        self.consecutive_no_spot += 1
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        do_switch = False
        if not is_tight and self.consecutive_no_spot >= 3 and num_regions > 1:
            next_region = (current_region + 1) % num_regions
            self.env.switch_region(next_region)
            self.consecutive_no_spot = 0
            do_switch = True

        return ClusterType.ON_DEMAND
