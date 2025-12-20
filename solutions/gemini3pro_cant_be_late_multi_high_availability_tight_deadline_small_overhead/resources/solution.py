import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "cant_be_late_strategy"

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
        Prioritize Spot instances to save cost, but switch to On-Demand
        if the deadline approaches to ensure completion.
        """
        # Current state
        current_time = self.env.elapsed_seconds
        remaining_time = self.deadline - current_time
        
        done_time = sum(self.task_done_time)
        remaining_work = self.task_duration - done_time
        
        # If task is done (or effectively done), pause
        if remaining_work <= 1e-6:
            return ClusterType.NONE

        # Calculate time needed to finish if we use On-Demand (guaranteed capacity)
        # If we are already on On-Demand, we just need to finish pending overhead + work
        # If not, we assume we need to incur the full restart overhead to switch/start OD
        overhead_cost = 0.0
        if last_cluster_type == ClusterType.ON_DEMAND:
            overhead_cost = self.remaining_restart_overhead
        else:
            overhead_cost = self.restart_overhead
            
        time_needed_od = remaining_work + overhead_cost
        
        # Panic Logic:
        # If remaining time is close to the minimum time required to finish with On-Demand,
        # we must switch to On-Demand to avoid the -100,000 penalty.
        # We add a safety buffer of 1.5 time steps (gaps) to account for discrete time steps
        # and potential interruptions if we were to try one last Spot step.
        buffer = 1.5 * self.env.gap_seconds
        
        if remaining_time < time_needed_od + buffer:
            return ClusterType.ON_DEMAND

        # Cost Optimization Logic:
        # If we have plenty of time, try to use Spot instances.
        if has_spot:
            return ClusterType.SPOT
        
        # If Spot is unavailable in the current region, switch to the next region.
        # We iterate regions in a round-robin fashion.
        num_regions = self.env.get_num_regions()
        current_region = self.env.get_current_region()
        next_region = (current_region + 1) % num_regions
        
        self.env.switch_region(next_region)
        
        # Return NONE for this step while we switch/search.
        # We will check availability in the new region in the next step.
        return ClusterType.NONE
