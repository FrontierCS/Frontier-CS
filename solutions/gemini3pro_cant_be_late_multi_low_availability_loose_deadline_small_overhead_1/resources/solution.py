import json
from argparse import Namespace
from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType

class Solution(MultiRegionStrategy):
    """
    Adaptive strategy that prioritizes Spot instances to minimize cost.
    It switches regions to search for Spot availability when slack permits,
    and falls back to On-Demand when the deadline approaches.
    """
    
    NAME = "adaptive_cost_optimizer"

    def solve(self, spec_path: str) -> "Solution":
        """Initialize the solution from spec_path config."""
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
        
        Strategy:
        1. Always use Spot if available in current region (Lowest Cost).
        2. If Spot unavailable:
           - If we have sufficient slack (time buffer), switch to next region and pause (NONE) 
             to check availability in the next step. This minimizes cost at the expense of time.
           - If slack is low, use On-Demand to guarantee completion.
        """
        # Calculate current progress
        done_time = sum(self.task_done_time)
        remaining_work = max(0.0, self.task_duration - done_time)
        time_elapsed = self.env.elapsed_seconds
        time_remaining = self.deadline - time_elapsed
        
        # Slack: Extra time available beyond required work duration
        slack = time_remaining - remaining_work
        
        # Environment parameters
        gap = self.env.gap_seconds
        overhead = self.restart_overhead
        
        # Safety buffer: Minimum slack required to handle restarts/overhead safely.
        # We keep 5x overhead as a margin to avoid deadline violation.
        safety_buffer = 5.0 * overhead

        # Priority 1: Use Spot if available
        if has_spot:
            return ClusterType.SPOT

        # Priority 2: Search other regions if we have enough time
        # We can search if we can afford to waste this timestep (gap) and still be safe.
        can_search = slack > (gap + safety_buffer)

        if can_search:
            # Switch to the next region in a round-robin fashion
            current_region = self.env.get_current_region()
            num_regions = self.env.get_num_regions()
            next_region = (current_region + 1) % num_regions
            self.env.switch_region(next_region)
            
            # Return NONE to "travel" to the new region without incurring OD costs.
            # In the next step, we will see if the new region has Spot.
            return ClusterType.NONE
        
        # Priority 3: Fallback to On-Demand to ensure deadline
        return ClusterType.ON_DEMAND
