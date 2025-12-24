import json
from argparse import Namespace
import numpy as np

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
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

        # --- Hyperparameters for the strategy ---
        self.EMA_ALPHA = 0.1
        self.ON_DEMAND_SAFETY_FACTOR = 25.0
        self.WAIT_SLACK_THRESHOLD_FACTOR = 5.0
        self.SWITCH_CONFIDENCE_THRESHOLD = 0.5
        self.EXPLORATION_WEIGHT = 0.15
        self.RECENCY_HALF_LIFE_SECONDS = 3.0 * 3600.0

        # --- State tracking ---
        self.num_regions = self.env.get_num_regions()
        
        self.spot_availability_ema = np.full(self.num_regions, 0.75)
        
        self.last_update_time = np.zeros(self.num_regions)
        
        self.visit_counts = np.zeros(self.num_regions)
        
        self.steps_counter = 0

        self.recency_decay_rate = np.log(2) / self.RECENCY_HALF_LIFE_SECONDS

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        self.steps_counter += 1
        current_region = self.env.get_current_region()
        time_elapsed = self.env.elapsed_seconds

        # 1. Update knowledge base with current observation
        current_ema = self.spot_availability_ema[current_region]
        self.spot_availability_ema[current_region] = (1 - self.EMA_ALPHA) * current_ema + self.EMA_ALPHA * float(has_spot)
        self.last_update_time[current_region] = time_elapsed
        self.visit_counts[current_region] += 1
        
        # 2. Calculate current state and urgency
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        
        if work_remaining <= 0:
            return ClusterType.NONE

        time_to_deadline = self.deadline - time_elapsed
        
        on_demand_panic_threshold = work_remaining + self.restart_overhead * self.ON_DEMAND_SAFETY_FACTOR

        if time_to_deadline <= on_demand_panic_threshold:
            return ClusterType.ON_DEMAND

        # 3. Main decision logic
        if has_spot:
            return ClusterType.SPOT

        # Spot is NOT available locally. Evaluate other options.
        
        # 3a. Evaluate other regions
        region_scores = np.copy(self.spot_availability_ema)
        
        time_since_update = time_elapsed - self.last_update_time
        decay_factor = np.exp(-self.recency_decay_rate * time_since_update)
        region_scores *= decay_factor
        
        # Add UCB1-like exploration bonus
        # Use self.steps_counter + 1 to avoid log(0).
        log_total_steps = np.log(self.steps_counter + 1)
        exploration_bonus = self.EXPLORATION_WEIGHT * np.sqrt(log_total_steps / (self.visit_counts + 1e-6))
        region_scores += exploration_bonus
        
        region_scores[current_region] = -np.inf
        
        best_other_region = np.argmax(region_scores)
        best_score = region_scores[best_other_region]

        # 3b. Make the final decision: switch, wait, or on-demand
        if best_score > self.SWITCH_CONFIDENCE_THRESHOLD:
            self.env.switch_region(best_other_region)
            return ClusterType.NONE
            
        slack_time = time_to_deadline - work_remaining
        wait_threshold = self.restart_overhead * self.WAIT_SLACK_THRESHOLD_FACTOR + self.env.gap_seconds

        if slack_time > wait_threshold:
            return ClusterType.NONE
        else:
            return ClusterType.ON_DEMAND
