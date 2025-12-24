import json
from argparse import Namespace
from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType
import math

class Solution(MultiRegionStrategy):
    NAME = "my_strategy"

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
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        remaining_work = self.task_duration - sum(self.task_done_time)
        remaining_time = self.deadline - self.env.elapsed_seconds
        
        # If no work left, do nothing
        if remaining_work <= 0:
            return ClusterType.NONE
        
        # Calculate time buffer needed for safety
        time_per_work_unit = self.env.gap_seconds
        safety_buffer = 2 * self.restart_overhead + time_per_work_unit
        
        # If we're in a restart overhead, wait
        if self.remaining_restart_overhead > 0:
            return ClusterType.NONE
        
        # Emergency mode: if we might miss deadline, use on-demand
        if remaining_time - safety_buffer < remaining_work:
            return ClusterType.ON_DEMAND
        
        # Try spot if available
        if has_spot:
            return ClusterType.SPOT
        
        # Spot not available - explore other regions
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        
        # Try to find a region with spot
        best_region = current_region
        best_score = -1
        
        # Simple heuristic: check adjacent regions
        for offset in range(1, num_regions):
            check_region = (current_region + offset) % num_regions
            # Switch temporarily to check (this is a conceptual check)
            # In reality we don't know has_spot in other regions without switching
            # We'll implement a simple round-robin exploration
            if offset == 1:  # Just try next region
                self.env.switch_region(check_region)
                # After switching, we need to return a cluster type
                # We'll return NONE for this step since we just switched
                return ClusterType.NONE
        
        # If we haven't switched region and no spot available, use on-demand
        # but only if we have enough time buffer
        if remaining_time - self.restart_overhead > remaining_work:
            # Wait for spot to potentially become available
            return ClusterType.NONE
        else:
            return ClusterType.ON_DEMAND
