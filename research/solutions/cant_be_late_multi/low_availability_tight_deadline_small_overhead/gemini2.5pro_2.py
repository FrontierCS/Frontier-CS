import json
import collections
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

        # Custom initialization for the strategy
        self.num_regions = self.env.get_num_regions()
        
        # Parameters for history tracking and decision making
        self.history_window = 10 
        self.spot_history = {
            i: collections.deque(maxlen=self.history_window) 
            for i in range(self.num_regions)
        }
        
        # Heuristic thresholds
        self.switch_score_threshold = 0.75
        self.wait_slack_factor = 0.5 
        
        # Pre-calculate initial slack for later decisions
        self.initial_slack = self.deadline - self.task_duration

        return self

    def _update_history(self, region: int, has_spot: bool):
        """Updates the spot availability history for a given region."""
        self.spot_history[region].append(1 if has_spot else 0)

    def _find_best_region_to_switch(self, current_region: int) -> tuple[int, float]:
        """
        Finds the best region to switch to based on historical spot availability.
        Returns the region index and its score.
        """
        scores = {}
        for r in range(self.num_regions):
            if r == current_region:
                continue
            
            history = self.spot_history[r]
            if not history:
                # Optimistically explore unvisited regions
                score = 1.0 
            else:
                score = sum(history) / len(history)
            scores[r] = score
        
        if not scores: # This happens in a single-region scenario
            return -1, -1.0
            
        best_region = max(scores, key=scores.get)
        return best_region, scores[best_region]

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        # 1. Calculate current progress and time state
        remaining_work = self.task_duration - sum(self.task_done_time)
        
        # If task is finished, do nothing to save cost.
        if remaining_work <= 0:
            return ClusterType.NONE

        time_to_deadline = self.deadline - self.env.elapsed_seconds
        current_region = self.env.get_current_region()

        # 2. Update historical data for the current region
        self._update_history(current_region, has_spot)

        # 3. PANIC MODE: Not enough time left even for guaranteed on-demand.
        if time_to_deadline <= remaining_work:
            return ClusterType.ON_DEMAND

        # 4. URGENT MODE: Not enough slack to risk a single spot preemption.
        spot_failure_time_cost = self.env.gap_seconds + self.restart_overhead
        if time_to_deadline <= remaining_work + spot_failure_time_cost:
            return ClusterType.ON_DEMAND

        # 5. REGULAR MODE: We have slack, so make cost-effective decisions.
        if has_spot:
            return ClusterType.SPOT
        else:
            # Spot is not available. Decide to switch, use on-demand, or wait.
            best_region, best_score = self._find_best_region_to_switch(current_region)
            
            switch_slack_cost = self.restart_overhead
            if best_score >= self.switch_score_threshold and \
               time_to_deadline > remaining_work + switch_slack_cost:
                
                self.env.switch_region(best_region)
                return ClusterType.ON_DEMAND

            current_slack = time_to_deadline - remaining_work
            wait_threshold_slack = self.initial_slack * self.wait_slack_factor
            
            if current_slack > wait_threshold_slack:
                return ClusterType.NONE
            else:
                return ClusterType.ON_DEMAND