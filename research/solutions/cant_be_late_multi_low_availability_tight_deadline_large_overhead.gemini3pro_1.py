import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

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
        self.consecutive_switches = 0
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # 1. Gather state
        elapsed = self.env.elapsed_seconds
        done = sum(self.task_done_time)
        remaining_work = self.task_duration - done
        time_left = self.deadline - elapsed
        gap = self.env.gap_seconds
        overhead = self.restart_overhead

        # 2. Panic Check: Calculate safety margin
        # If we switch to OD or start OD, we might incur overhead.
        # If already on OD, overhead is 0.
        overhead_penalty = 0 if last_cluster_type == ClusterType.ON_DEMAND else overhead
        
        # Time strictly required to finish on OD
        min_time_needed = remaining_work + overhead_penalty
        
        # Buffer to account for step quantization and minor delays.
        # 2.5 * gap ensures we have at least 2 full steps of buffer.
        safety_threshold = min_time_needed + (2.5 * gap)

        # If time is running out, force On-Demand to guarantee completion
        if time_left < safety_threshold:
            self.consecutive_switches = 0
            return ClusterType.ON_DEMAND

        # 3. Strategy Logic
        if has_spot:
            # Cheapest option available
            self.consecutive_switches = 0
            return ClusterType.SPOT
        else:
            # Spot unavailable in current region.
            # Check if we should search other regions or fallback to OD.
            
            num_regions = self.env.get_num_regions()
            slack = time_left - min_time_needed
            
            # If we have significant slack (>4 hours/steps), we can afford to search.
            # Limit consecutive switches to prevent infinite loops without progress.
            if slack > 4.0 * gap and self.consecutive_switches < num_regions:
                curr_region = self.env.get_current_region()
                next_region = (curr_region + 1) % num_regions
                self.env.switch_region(next_region)
                self.consecutive_switches += 1
                
                # Return NONE to wait one tick and check availability in new region
                return ClusterType.NONE
            
            # Fallback: Not enough slack or all regions checked
            self.consecutive_switches = 0
            return ClusterType.ON_DEMAND