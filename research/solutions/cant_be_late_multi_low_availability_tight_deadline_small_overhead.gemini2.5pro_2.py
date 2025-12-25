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
        
        self.num_regions = len(config.get("trace_files", []))
        self.last_spot_seen = [-1.0] * self.num_regions
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        work_done = sum(self.task_done_time)
        work_rem = self.task_duration - work_done
        
        if work_rem <= 0:
            return ClusterType.NONE

        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()

        if has_spot:
            self.last_spot_seen[current_region] = self.env.elapsed_seconds

        # Safety Net: Force On-Demand if the deadline is critical
        on_demand_finish_time = self.env.elapsed_seconds + self.restart_overhead + work_rem
        
        if on_demand_finish_time >= self.deadline:
            return ClusterType.ON_DEMAND

        # Primary Strategy: Prioritize Spot for cost savings
        if has_spot:
            return ClusterType.SPOT
        
        # Spot not available: Wait and switch to a better region
        else:
            if num_regions > 1:
                best_region_to_switch = -1
                max_seen_time = -1.0
                
                for r in range(num_regions):
                    if r == current_region:
                        continue
                    if self.last_spot_seen[r] > max_seen_time:
                        max_seen_time = self.last_spot_seen[r]
                        best_region_to_switch = r

                # If no other region has a known spot history, explore.
                if best_region_to_switch == -1:
                    best_region_to_switch = (current_region + 1) % num_regions
            
                self.env.switch_region(best_region_to_switch)

            # Wait (NONE) to save costs. The safety net will catch us if needed.
            return ClusterType.NONE
