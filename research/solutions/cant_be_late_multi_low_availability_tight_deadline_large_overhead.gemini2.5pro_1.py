import json
from argparse import Namespace
import math

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """
    A multi-region scheduling strategy that uses the UCB1 algorithm for 
    balancing exploration and exploitation across regions, combined with a 
    conservative "panic mode" to guarantee deadline completion.

    The core logic is as follows:
    1.  Maintain a probabilistic model (Beta-Bernoulli) for spot availability in each region.
    2.  If the deadline is approaching (Panic Mode), switch to On-Demand to guarantee completion.
        This is determined by checking if the current time slack is less than the cost of a
        single spot preemption.
    3.  If not in panic mode and Spot is available, always use it due to its low cost.
    4.  If Spot is unavailable, use the UCB1 algorithm to score each region. This score
        balances the estimated spot probability (exploitation) with the uncertainty of
        less-visited regions (exploration).
    5.  If a different region has a significantly higher UCB score, switch to it to find
        better spot availability. A switch is followed by an On-Demand step to ensure progress.
    6.  If not switching, decide whether to wait (NONE) or use On-Demand. This decision is
        based on the amount of slack time available. If slack is high, wait for Spot to return.
        Otherwise, use On-Demand to avoid falling behind schedule.
    """

    NAME = "ucb_scheduler"

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
        
        self.initialized = False
        return self

    def _initialize(self):
        """
        Lazy initialization on the first call to _step, once self.env is available.
        """
        self.num_regions = self.env.get_num_regions()
        
        # Bayesian estimation of spot probability using a Beta distribution prior.
        # alpha_params tracks successes (spot available), beta_params tracks failures.
        # Initializing with (1,1) corresponds to a uniform prior.
        self.alpha_params = [1.0] * self.num_regions
        self.beta_params = [1.0] * self.num_regions
        
        self.last_region = self.env.get_current_region()
        self.steps_in_current_region = 0
        self.total_steps = 0
        
        # --- Hyperparameters ---
        # UCB exploration factor. Higher values encourage more exploration.
        self.exploration_factor = 0.5
        # Minimum steps to stay in a region to prevent frantic switching.
        self.min_stay_steps = 3
        # UCB score margin required to trigger a region switch.
        self.switch_margin_ucb = 0.1
        # Slack time (as a multiple of gap_seconds) needed to justify waiting (NONE).
        self.wait_slack_factor = 5.0
        
        self.initialized = True

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        if not self.initialized:
            self._initialize()

        # --- 1. State and Model Update ---
        self.total_steps += 1
        current_region = self.env.get_current_region()
        
        if self.last_region != current_region:
            self.steps_in_current_region = 0
        self.steps_in_current_region += 1
        self.last_region = current_region

        if has_spot:
            self.alpha_params[current_region] += 1
        else:
            self.beta_params[current_region] += 1

        # --- 2. Calculate Metrics ---
        remaining_work = self.task_duration - sum(self.task_done_time)
        if remaining_work <= 0:
            return ClusterType.NONE

        remaining_time = self.deadline - self.env.elapsed_seconds

        # --- 3. Panic Mode (Highest Priority) ---
        slack = remaining_time - remaining_work
        # A single spot failure costs one step of work (gap) plus the restart overhead.
        # If our slack is less than this, we cannot risk a preemption.
        spot_failure_cost = self.env.gap_seconds + self.restart_overhead
        if slack < spot_failure_cost:
            return ClusterType.ON_DEMAND

        # --- 4. Greedy Spot (If available and not in panic) ---
        if has_spot:
            return ClusterType.SPOT

        # --- 5. No Spot Available Logic ---
        # Choices: ON_DEMAND, SWITCH+ON_DEMAND, or NONE.

        # 5a. Region Switching Decision (UCB1)
        scores = []
        for i in range(self.num_regions):
            mean_prob = self.alpha_params[i] / (self.alpha_params[i] + self.beta_params[i])
            visits = self.alpha_params[i] + self.beta_params[i] - 2.0
            
            if visits == 0:
                exploration_bonus = 1e9  # Prioritize unvisited regions
            else:
                exploration_bonus = self.exploration_factor * math.sqrt(math.log(self.total_steps) / visits)
            scores.append(mean_prob + exploration_bonus)

        current_score = scores[current_region]
        best_alt_region = -1
        best_alt_score = -1.0
        for i in range(self.num_regions):
            if i == current_region:
                continue
            if scores[i] > best_alt_score:
                best_alt_score = scores[i]
                best_alt_region = i
        
        # Switch if a better alternative exists and we've stayed long enough.
        if (best_alt_region != -1 and 
            best_alt_score > current_score + self.switch_margin_ucb and
            self.steps_in_current_region >= self.min_stay_steps):
            
            self.env.switch_region(best_alt_region)
            # Per API, if has_spot is False, cannot return SPOT. Using ON_DEMAND
            # after a switch ensures we make progress.
            return ClusterType.ON_DEMAND

        # 5b. Stay in Region Decision (Wait or Work)
        # If not switching, decide between ON_DEMAND and NONE.
        wait_threshold_slack = self.wait_slack_factor * self.env.gap_seconds
        if slack > wait_threshold_slack:
            # We have enough slack to wait for spot to potentially return.
            return ClusterType.NONE
        else:
            # Not enough slack to wait, must make progress with ON_DEMAND.
            return ClusterType.ON_DEMAND
