import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "my_strategy"

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
        )
        super().__init__(args)
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        Prioritize finishing before deadline, then minimizing cost.
        """
        # Calculate remaining work and time
        current_done = sum(self.task_done_time)
        work_remaining = self.task_duration - current_done
        time_remaining = self.deadline - self.env.elapsed_seconds
        
        # Calculate slack: how much time we can afford to waste/wait
        slack = time_remaining - work_remaining
        
        # Define a safety margin (e.g., 4 hours).
        # If slack drops below this, we must use On-Demand to guarantee the deadline.
        # This buffer accounts for potential restart overheads and future unavailability.
        SAFE_MARGIN_SECONDS = 4 * 3600.0
        
        # Strategy Logic
        
        # 1. Critical Phase: Low slack
        if slack < SAFE_MARGIN_SECONDS:
            # If we are close to the deadline, stop optimizing for cost.
            # Use On-Demand to ensure we finish. OD is reliable and won't be preempted.
            return ClusterType.ON_DEMAND
            
        # 2. Optimization Phase: High slack
        if has_spot:
            # If Spot is available and we have time, use it.
            # It is significantly cheaper than On-Demand.
            return ClusterType.SPOT
        else:
            # Spot is unavailable in the current region, but we have plenty of slack.
            # Instead of paying for On-Demand immediately, we switch regions to 'hunt' for Spot.
            # We return NONE (pause) for this step to avoid paying OD cost while switching.
            # In the next step, we will be in the new region and check its Spot availability.
            current_region_idx = self.env.get_current_region()
            num_regions = self.env.get_num_regions()
            
            # cycle to next region
            next_region_idx = (current_region_idx + 1) % num_regions
            self.env.switch_region(next_region_idx)
            
            return ClusterType.NONE