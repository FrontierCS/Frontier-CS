import json
import math
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

        # Custom initialization for the strategy's state
        self.num_regions = len(config["trace_files"])
        self.spot_history = {}
        for i in range(self.num_regions):
            self.spot_history[i] = {
                'visits': 0,
                'successes': 0,
                'prob': 0.5,
            }
        
        self.total_steps = 0
        # Exploration constant for UCB1, sqrt(2) is a common choice
        self.ucb_c = math.sqrt(2)
        # UCB score threshold to justify the cost of switching regions
        self.SWITCH_THRESHOLD = 0.7

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        self.total_steps += 1
        current_region = self.env.get_current_region()

        # 1. Update historical data for the current region
        history = self.spot_history[current_region]
        history['visits'] += 1
        if has_spot:
            history['successes'] += 1
        
        if history['visits'] > 0:
            history['prob'] = history['successes'] / history['visits']

        # 2. Check for task completion
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done

        if work_remaining <= 0:
            return ClusterType.NONE

        # 3. Assess deadline risk (Panic Mode)
        time_left = self.deadline - self.env.elapsed_seconds
        
        # Calculate the time required to finish if we switch to on-demand now.
        # This is a worst-case estimate, assuming we incur a full restart overhead.
        guaranteed_completion_duration = work_remaining + self.restart_overhead
        
        # A safety margin of two steps. This gives us one chance to try a risky
        # move (like switching regions and failing) before we are forced into panic mode.
        safety_margin = 2 * self.env.gap_seconds

        if time_left <= guaranteed_completion_duration + safety_margin:
            return ClusterType.ON_DEMAND

        # 4. Normal Operation (sufficient slack time)
        if has_spot:
            # Happy path: cheap spot instance is available.
            return ClusterType.SPOT
        else:
            # Spot is not available. Decide between switching region or waiting.
            # Using ON_DEMAND is avoided here to minimize cost.

            # Find the best alternative region using UCB1 algorithm
            best_other_region = -1
            max_ucb_score = -1.0

            for i in range(self.num_regions):
                if i == current_region:
                    continue

                hist = self.spot_history[i]
                if hist['visits'] == 0:
                    # Prioritize exploring unvisited regions
                    best_other_region = i
                    max_ucb_score = float('inf')
                    break
                
                # UCB = exploitation (mean) + exploration (confidence bound)
                exploitation = hist['prob']
                exploration = self.ucb_c * math.sqrt(math.log(self.total_steps) / hist['visits'])
                ucb_score = exploitation + exploration

                if ucb_score > max_ucb_score:
                    max_ucb_score = ucb_score
                    best_other_region = i
            
            # Decide whether to switch based on the UCB score of the best alternative
            if max_ucb_score > self.SWITCH_THRESHOLD and best_other_region != -1:
                # A different region looks promising enough to be worth the switch cost
                self.env.switch_region(best_other_region)
                # Gamble that the new region has a spot instance available
                return ClusterType.SPOT
            else:
                # No other region looks promising, so wait in the current region.
                # This costs nothing and saves our slack for later.
                return ClusterType.NONE