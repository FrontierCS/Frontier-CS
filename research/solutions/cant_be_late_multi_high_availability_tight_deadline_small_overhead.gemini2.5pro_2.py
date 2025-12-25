import json
import math
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """
    A multi-region scheduling strategy that uses the UCB1 algorithm to balance
    exploration of regions with exploitation of regions with high spot availability.
    The core idea is to use cheap spot instances as much as possible, while
    constantly monitoring the progress against the deadline. If the time remaining
    becomes critical, it switches to reliable on-demand instances to guarantee
    completion. When spot is unavailable in the current region, it proactively
    switches to another region predicted to have better availability by the UCB1
    algorithm, rather than waiting idly.
    """

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

        self.num_regions = self.env.get_num_regions()
        
        # Statistics for the UCB1 algorithm to track spot availability per region
        self.region_spot_probes = [0] * self.num_regions
        self.region_spot_successes = [0] * self.num_regions
        self.total_probes = 0
        
        # UCB1 exploration hyperparameter. A value around 1.0 is a common choice.
        self.EXPLORATION_CONSTANT = 1.0

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        # 1. Update statistics for our region selection algorithm (UCB1)
        current_region = self.env.get_current_region()
        self.total_probes += 1
        self.region_spot_probes[current_region] += 1
        if has_spot:
            self.region_spot_successes[current_region] += 1

        # 2. Calculate current progress and time remaining
        done_work = sum(self.task_done_time)
        remaining_work = self.task_duration - done_work

        # If the task is finished, do nothing to save costs.
        if remaining_work <= 1e-9:
            return ClusterType.NONE

        remaining_time = self.deadline - self.env.elapsed_seconds
        
        # 3. Determine if we are in a "panic mode" where we must use on-demand
        gap = self.env.gap_seconds
        
        # Calculate the absolute minimum time required to finish the job using
        # only reliable on-demand instances from this point forward.
        if gap > 1e-9:
            steps_needed_for_on_demand = math.ceil(remaining_work / gap)
            time_needed_for_on_demand = steps_needed_for_on_demand * gap
        else:
            # If gap is zero or negligible, we can't make progress.
            time_needed_for_on_demand = float('inf')

        # If the time we have left is less than or equal to the minimum time
        # required, we must use on-demand to avoid missing the deadline.
        if remaining_time <= time_needed_for_on_demand:
            return ClusterType.ON_DEMAND

        # 4. If not in panic mode, make a cost-effective decision
        if has_spot:
            # Spot is available, and we have enough time buffer. Use the cheap option.
            return ClusterType.SPOT
        else:
            # Spot is not available in the current region.
            # Switch to another region hoping for better spot availability.

            # Use UCB1 to choose the most promising region.
            # First, prioritize any region we have never visited.
            unexplored_regions = [
                i for i, probes in enumerate(self.region_spot_probes)
                if probes == 0 and i != current_region
            ]

            if unexplored_regions:
                # Switch to the first unexplored region to gather data.
                best_region_to_switch = unexplored_regions[0]
            else:
                # All other regions have been visited. Choose the one with the
                # highest UCB score (balancing success rate and uncertainty).
                best_region_to_switch = -1
                max_score = -1.0
                
                log_total_probes = math.log(self.total_probes) if self.total_probes > 0 else 0

                for i in range(self.num_regions):
                    if i == current_region:
                        continue
                    
                    probes = self.region_spot_probes[i]
                    success_rate = self.region_spot_successes[i] / probes
                    exploration_term = self.EXPLORATION_CONSTANT * math.sqrt(log_total_probes / probes)
                    score = success_rate + exploration_term

                    if score > max_score:
                        max_score = score
                        best_region_to_switch = i
            
            # Failsafe: if no region is selected (shouldn't happen if num_regions > 1),
            # just cycle to the next one.
            if best_region_to_switch == -1:
                best_region_to_switch = (current_region + 1) % self.num_regions

            self.env.switch_region(best_region_to_switch)
            
            # After deciding to switch, do nothing for the rest of this step.
            # The switch itself costs time and incurs an overhead for the next step.
            return ClusterType.NONE
