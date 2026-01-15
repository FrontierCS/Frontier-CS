import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Adaptive multi-region scheduling strategy minimizing cost while meeting deadlines."""

    NAME = "adaptive_search_strategy"

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the solution from spec_path config.
        """
        with open(spec_path) as f:
            config = json.load(f)

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
            trace_files=config.get("trace_files", [])
        )
        super().__init__(args)
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        
        Strategy:
        1. Calculate safety margin: Ensure we have enough time to finish the work on On-Demand
           instances (worst case), including restart overheads and a safety buffer.
        2. Panic Mode: If time is running low (below safety margin), switch to On-Demand immediately
           and stick with it to guarantee completion.
        3. Search Mode: If we have plenty of slack:
           - If Spot is available in current region, use it (minimize cost).
           - If Spot is unavailable, switch to the next region and wait (NONE) for one step
             to check availability there. This allows us to traverse regions to find Spot
             capacity without paying On-Demand prices, using our slack time as currency.
        """
        # 1. State Assessment
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        time_remaining = self.deadline - self.env.elapsed_seconds
        
        # 2. Panic Threshold Calculation
        # We reserve enough time to complete the work plus one restart overhead.
        # We add a 2-hour (7200s) buffer to account for search steps or granularity.
        safety_buffer_seconds = 7200.0
        required_time_for_completion = work_remaining + self.restart_overhead + safety_buffer_seconds
        
        # 3. Decision Logic
        
        # Priority 1: Guarantee Deadline (Panic Mode)
        if time_remaining < required_time_for_completion:
            return ClusterType.ON_DEMAND

        # Priority 2: Minimize Cost (Search Mode)
        if has_spot:
            # Optimal state: Safe to run and Spot is available
            return ClusterType.SPOT
        else:
            # Spot unavailable in current region, but we have time to search.
            # Switch region and pause (NONE) to inspect next region's availability in next step.
            num_regions = self.env.get_num_regions()
            current_region = self.env.get_current_region()
            
            # Round-robin region switching
            next_region = (current_region + 1) % num_regions
            self.env.switch_region(next_region)
            
            # Return NONE to avoid errors (cannot schedule SPOT if unavailable) 
            # and to minimize cost while the switch/check occurs.
            return ClusterType.NONE