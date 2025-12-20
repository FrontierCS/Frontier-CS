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

        # A safety factor to determine when to switch to On-Demand.
        # If remaining slack is less than SAFETY_FACTOR * restart_overhead,
        # we switch to On-Demand to guarantee finishing on time.
        self.SAFETY_FACTOR = 5.0
        
        # Track consecutive spot unavailability for each region to inform
        # switching decisions.
        num_regions = self.env.get_num_regions()
        self.consecutive_spot_failures = [0] * num_regions

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        # 1. If the task is done, stop incurring costs.
        work_done = sum(self.task_done_time)
        if work_done >= self.task_duration:
            return ClusterType.NONE

        # 2. Calculate remaining work, time, and slack.
        work_rem = self.task_duration - work_done
        time_rem_deadline = self.deadline - self.env.elapsed_seconds
        slack_time = time_rem_deadline - work_rem

        # 3. Safety Net: Prioritize finishing before the deadline.
        # If slack time is critically low, switch to On-Demand.
        critical_buffer = self.restart_overhead * self.SAFETY_FACTOR
        if slack_time <= critical_buffer:
            return ClusterType.ON_DEMAND

        current_region = self.env.get_current_region()

        # 4. Main Strategy: Use Spot if available, otherwise find a better region.
        if has_spot:
            # Spot is available and we have plenty of slack. Use it for cost savings.
            self.consecutive_spot_failures[current_region] = 0
            return ClusterType.SPOT
        else:
            # Spot is not available in the current region.
            self.consecutive_spot_failures[current_region] += 1
            
            num_regions = self.env.get_num_regions()
            if num_regions > 1:
                # If other regions exist, switch to the most promising one.
                # "Most promising" is the one with the fewest observed consecutive
                # Spot failures.
                candidate_regions = []
                for i in range(num_regions):
                    if i != current_region:
                        candidate_regions.append((self.consecutive_spot_failures[i], i))
                
                # Sort by failure count, then by region index for determinism.
                candidate_regions.sort()
                
                best_region_to_switch = candidate_regions[0][1]
                
                self.env.switch_region(best_region_to_switch)
                
                # After switching, pause for one step to observe the new region's
                # Spot availability.
                return ClusterType.NONE
            else:
                # No other regions to switch to. We must wait.
                return ClusterType.NONE
