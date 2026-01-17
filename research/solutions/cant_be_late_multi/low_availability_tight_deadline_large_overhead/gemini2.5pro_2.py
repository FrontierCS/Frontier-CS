import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "adaptive_risk_averse_strategy"  # REQUIRED: unique identifier

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

        # Custom initialization
        self.num_regions = self.env.get_num_regions()
        
        # A small number of samples before we trust the availability ratio
        self.min_samples_for_ratio = 3
        
        # Stats for each region: number of times seen, and number of times spot was available
        self.region_stats = [{'seen': 0, 'available': 0} for _ in range(self.num_regions)]
        
        # Track the step number of the last visit to each region for LRU tie-breaking
        self.last_visit_step = [-1] * self.num_regions
        self.step_counter = 0

        # Safety buffer factor for determining the critical threshold.
        # We switch to ON_DEMAND if slack is less than this factor times the restart overhead.
        self.safety_buffer_factor = 2.0

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        self.step_counter += 1
        current_region = self.env.get_current_region()

        # Update stats for the current region based on the `has_spot` info.
        self.region_stats[current_region]['seen'] += 1
        if has_spot:
            self.region_stats[current_region]['available'] += 1
        self.last_visit_step[current_region] = self.step_counter

        # 1. Calculate current work and time metrics
        work_done = sum(self.task_done_time)
        work_rem = self.task_duration - work_done
        
        # If the task is finished, do nothing.
        if work_rem <= 0:
            return ClusterType.NONE

        time_rem = self.deadline - self.env.elapsed_seconds
        effective_work_rem = work_rem + self.remaining_restart_overhead
        
        # Absolute deadline failure condition: even non-stop on-demand is not enough.
        if time_rem < effective_work_rem:
            return ClusterType.ON_DEMAND

        # 2. Check for CRITICAL condition: switch to On-Demand if slack is low.
        critical_threshold = self.safety_buffer_factor * self.restart_overhead
        slack = time_rem - effective_work_rem
        
        if slack <= critical_threshold:
            # Not enough slack to risk any more interruptions. Use guaranteed On-Demand.
            return ClusterType.ON_DEMAND

        # 3. SPOT-SEEKING mode: not critical, try to use Spot.
        if has_spot:
            # Best case: Spot is available and we have enough slack.
            return ClusterType.SPOT
        else:
            # Spot is not available in the current region. Decide whether to switch.
            if self.num_regions <= 1:
                # No other regions to switch to. Must use On-Demand to make progress.
                return ClusterType.ON_DEMAND

            # Calculate if switching is safe. A switch costs one restart_overhead.
            projected_effective_work_after_switch = work_rem + self.restart_overhead
            projected_slack_after_switch = time_rem - projected_effective_work_after_switch

            if projected_slack_after_switch > critical_threshold:
                # It's safe to switch. Find the best region to switch to.
                candidate_regions = []
                for i in range(self.num_regions):
                    if i == current_region:
                        continue
                    
                    stats = self.region_stats[i]
                    time_since_last_visit = self.step_counter - self.last_visit_step[i]

                    if stats['seen'] < self.min_samples_for_ratio:
                        # Prioritize unexplored regions. Break ties with LRU (longer since last visit is better).
                        # Score is a tuple for lexicographical comparison. A large number represents "unexplored".
                        score = (1e9, time_since_last_visit)
                    else:
                        ratio = stats['available'] / stats['seen']
                        # Prioritize high availability ratio. Break ties with LRU.
                        score = (ratio, time_since_last_visit)
                    
                    candidate_regions.append((score, i))
                
                # Sort candidates by score (descending)
                candidate_regions.sort(key=lambda x: x[0], reverse=True)
                best_region = candidate_regions[0][1]
                
                self.env.switch_region(best_region)
                # After switching, we don't know the new region's spot availability.
                # So we wait one step (NONE) and decide in the next _step call.
                return ClusterType.NONE
            else:
                # Not safe to switch (would leave us with too little slack).
                # Must use On-Demand in the current region to make progress.
                return ClusterType.ON_DEMAND