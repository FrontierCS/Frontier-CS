import json
import math
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """
    A multi-region scheduling strategy that uses an Upper Confidence Bound (UCB1)
    algorithm to balance exploration and exploitation of regions with high spot
    instance availability, coupled with a robust safety net to guarantee task
    completion before the deadline.
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

        # Custom initialization for the strategy
        self.num_regions = self.env.get_num_regions()

        # --- UCB1 multi-armed bandit parameters ---
        # Exploration constant
        self.ucb_c = 2.0
        # Optimistic initialization to encourage exploration and avoid division by zero
        self.region_visits = [1] * self.num_regions
        self.region_spot_hits = [0.5] * self.num_regions

        # --- Strategy control parameters ---
        # Counter for consecutive time steps with no spot availability
        self.consecutive_no_spot = 0
        # Buffer time for the on-demand safety net to ensure robustness
        self.on_demand_buffer = self.env.gap_seconds + self.restart_overhead
        # Threshold for consecutive no-spot steps before triggering a region switch
        self.switch_threshold = 2
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        current_region = self.env.get_current_region()

        # 1. Update historical data for the current region (for UCB)
        self.region_visits[current_region] += 1
        if has_spot:
            self.region_spot_hits[current_region] += 1
        
        # Update consecutive no-spot counter for the current stay in this region
        if has_spot:
            self.consecutive_no_spot = 0
        else:
            self.consecutive_no_spot += 1

        # 2. Check if the task is already finished
        remaining_work = self.task_duration - sum(self.task_done_time)
        if remaining_work <= 0:
            return ClusterType.NONE

        # 3. On-Demand Safety Net: guarantee completion before the deadline
        time_needed_on_demand = remaining_work + self.remaining_restart_overhead
        time_to_deadline = self.deadline - self.env.elapsed_seconds

        if time_to_deadline <= time_needed_on_demand + self.on_demand_buffer:
            return ClusterType.ON_DEMAND

        # 4. Greedily use Spot if available (primary cost-saving measure)
        if has_spot:
            return ClusterType.SPOT

        # 5. Handle No Spot: Decide whether to wait or switch regions
        if self.consecutive_no_spot >= self.switch_threshold:
            # We've waited long enough. Use UCB1 to find a more promising region.
            best_region_to_switch = -1
            max_ucb = -1.0
            total_visits = sum(self.region_visits)
            
            candidate_regions = [i for i in range(self.num_regions) if i != current_region]
            if not candidate_regions:
                # Only one region available, so we must wait.
                return ClusterType.NONE

            for i in candidate_regions:
                mean_reward = self.region_spot_hits[i] / self.region_visits[i]
                exploration_term = self.ucb_c * (
                    (math.log(total_visits) / self.region_visits[i])**0.5)
                ucb_score = mean_reward + exploration_term

                if ucb_score > max_ucb:
                    max_ucb = ucb_score
                    best_region_to_switch = i
            
            if best_region_to_switch != -1:
                self.env.switch_region(best_region_to_switch)
                self.consecutive_no_spot = 0  # Reset counter after switch
                # After switching, wait (NONE) to observe the new region's status.
                return ClusterType.NONE

        # If spot is unavailable but we haven't hit the switch threshold, wait.
        return ClusterType.NONE