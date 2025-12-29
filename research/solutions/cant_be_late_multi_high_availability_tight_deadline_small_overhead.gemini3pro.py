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
        """
        # Calculate current state
        elapsed = self.env.elapsed_seconds
        done = sum(self.task_done_time)
        remaining_work = self.task_duration - done
        
        # If task is effectively complete
        if remaining_work <= 1e-6:
            return ClusterType.NONE

        # Panic Logic: Switch to ON_DEMAND if time is running out.
        # We calculate the latest possible time to switch to OD to ensure completion.
        # Cost of switching/starting OD: self.restart_overhead.
        # We add a safety buffer consisting of:
        # 1. restart_overhead (to cover the switch cost)
        # 2. 2.0 * gap_seconds (to cover step quantization/loss of current step)
        # 3. Small margin (0.1 * overhead)
        
        gap = self.env.gap_seconds
        overhead = self.restart_overhead
        
        # Time required to finish if we start OD now (conservative estimate)
        time_to_finish_od = remaining_work + overhead
        
        # Buffer to trigger the switch before it's too late
        safety_buffer = gap * 2.0 + overhead * 0.1
        
        if elapsed + time_to_finish_od + safety_buffer >= self.deadline:
            return ClusterType.ON_DEMAND

        # Strategy: Prefer Spot if available.
        if has_spot:
            return ClusterType.SPOT
        else:
            # Spot not available in current region.
            # Strategy: Switch to the next region and wait (NONE) one step to check its availability.
            # We prefer to explore regions rather than wait in a bad region or pay for OD prematurely.
            
            curr_region = self.env.get_current_region()
            num_regions = self.env.get_num_regions()
            next_region = (curr_region + 1) % num_regions
            
            self.env.switch_region(next_region)
            
            # We return NONE because:
            # 1. 'has_spot' refers to the old region.
            # 2. We don't know if the new region has spot.
            # 3. Returning SPOT when unavailable raises an error.
            # 4. Waiting one step allows us to poll the new region's status in the next _step call.
            return ClusterType.NONE