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
        # Gather current state parameters
        elapsed = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        done_time = sum(self.task_done_time)
        
        # Static parameters
        total_duration = self.task_duration
        deadline = self.deadline
        overhead = self.restart_overhead
        
        remaining_work = total_duration - done_time
        remaining_time = deadline - elapsed
        
        # Calculate Slack: Time buffer available beyond mandatory work and restart overhead.
        # We subtract overhead to account for the potential cost of switching/starting OD.
        slack = remaining_time - remaining_work - overhead
        
        # Safety Threshold: When to force On-Demand.
        # We need enough slack to absorb the time cost of probing (waiting 'gap' seconds) 
        # or a failed Spot step. If slack drops below ~1.5x the step size, we are in danger 
        # of missing the deadline if the next Spot attempt fails or if we probe.
        panic_threshold = gap * 1.5
        
        # Panic Mode: Force On-Demand if slack is too low to guarantee completion otherwise
        if slack < panic_threshold:
            return ClusterType.ON_DEMAND
        
        # Spot Availability Mode: If Spot is available and we have slack, use it
        if has_spot:
            return ClusterType.SPOT
            
        # Hunt Mode: No Spot in current region, but we have slack.
        # Switch to the next region and wait (NONE) to probe availability in the next step.
        # Returning NONE ensures we don't crash by requesting SPOT on an unavailable region,
        # and minimizes cost while we search for a region with Spot availability.
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        next_region = (current_region + 1) % num_regions
        
        self.env.switch_region(next_region)
        return ClusterType.NONE