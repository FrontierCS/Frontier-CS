import json
from argparse import Namespace
import math

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "my_strategy"  # REQUIRED: unique identifier

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the solution from spec_path config.

        The spec file contains:
        - deadline: deadline in hours
        - duration: task duration in hours
        - overhead: restart overhead in hours
        - trace_files: list of trace file paths (one per region)
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

        self.num_regions = len(config["trace_files"])
        
        # Bayesian estimates for spot availability, using a Beta distribution prior.
        # Corresponds to a prior belief of high availability, based on problem description.
        # We model successes (alpha) and failures (beta).
        # Prior is equivalent to observing ~4 successes and 1 failure.
        self.prior_alpha = 4.0 
        self.prior_beta = 1.0

        # Track observations: successes (alpha) and attempts (alpha + beta)
        self.spot_successes = [0] * self.num_regions
        self.spot_attempts = [0] * self.num_regions
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        # 1. Update historical statistics for the current region
        current_region = self.env.get_current_region()
        self.spot_attempts[current_region] += 1
        if has_spot:
            self.spot_successes[current_region] += 1

        # 2. Check for task completion
        remaining_work = self.task_duration - sum(self.task_done_time)
        if remaining_work <= 0:
            return ClusterType.NONE

        # 3. Deadline criticality check (Safety Net)
        time_left = self.deadline - self.env.elapsed_seconds
        
        # Calculate time needed to finish if we must switch to On-Demand now
        overhead_for_od = 0
        if last_cluster_type != ClusterType.ON_DEMAND:
            overhead_for_od = self.restart_overhead
        
        total_overhead_if_od = max(self.remaining_restart_overhead, overhead_for_od)
        time_needed_for_od_finish = total_overhead_if_od + remaining_work
        
        # Use a safety buffer to avoid cutting it too close
        safety_buffer = self.env.gap_seconds * 1.5
        if time_left <= time_needed_for_od_finish + safety_buffer:
            return ClusterType.ON_DEMAND

        # 4. Main decision logic
        if has_spot:
            # If spot is available, it's the most cost-effective choice.
            return ClusterType.SPOT
        else:
            # Spot is not available. Decide between switching or using On-Demand.
            
            # Find the best alternative region to switch to based on posterior mean
            scores = []
            for i in range(self.num_regions):
                if i == current_region:
                    scores.append(-1.0)  # Don't consider the current region
                else:
                    # Bayesian posterior mean: (prior_successes + observed_successes) / (total_prior_obs + total_observed_obs)
                    posterior_alpha = self.prior_alpha + self.spot_successes[i]
                    posterior_beta = self.prior_beta + (self.spot_attempts[i] - self.spot_successes[i])
                    score = posterior_alpha / (posterior_alpha + posterior_beta)
                    scores.append(score)
            
            best_next_region = scores.index(max(scores))
            best_score = scores[best_next_region]

            # Decide whether to switch based on available "slack" time
            slack = time_left - remaining_work
            
            # The more confident we are about the next region (higher score),
            # the less slack we require to justify the risk of a switch.
            base_slack_requirement = self.restart_overhead * 2.0
            
            # Adjust slack requirement based on confidence.
            # A score of 1.0 (high confidence) uses the base requirement.
            # A score of 0.0 (low confidence) doubles the requirement.
            # A score near the prior mean (~0.8) results in a moderate requirement.
            slack_requirement = base_slack_requirement * (1.0 + (1.0 - best_score))
            
            if slack > slack_requirement:
                # We have enough slack to risk a switch.
                self.env.switch_region(best_next_region)
                # Use NONE to absorb the switch overhead without cost.
                # The next time step will start in the new region.
                return ClusterType.NONE
            else:
                # Not enough slack to risk it. Use On-Demand to guarantee progress.
                return ClusterType.ON_DEMAND