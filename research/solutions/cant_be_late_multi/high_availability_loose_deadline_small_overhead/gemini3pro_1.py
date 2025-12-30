import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Adaptive strategy that prioritizes Spot instances and switches regions when unavailable."""

    NAME = "AdaptiveCostOptimizer"

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
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        Strategically switches regions if Spot is unavailable and slack permits.
        Falls back to On-Demand if deadline approaches.
        """
        # Calculate current progress and remaining work
        done_time = sum(self.task_done_time)
        rem_work = self.task_duration - done_time
        
        # Check if job is effectively finished
        if rem_work <= 1e-5:
            return ClusterType.NONE

        elapsed = self.env.elapsed_seconds
        time_left = self.deadline - elapsed
        
        # Calculate slack: available buffer time beyond minimum required
        # We subtract remaining_restart_overhead to be conservative about pending delays
        slack = time_left - (rem_work + self.remaining_restart_overhead)
        
        gap = self.env.gap_seconds
        
        # Thresholds definition
        # Critical Threshold: If slack drops below this, we risk missing the deadline.
        # We use 1.5x step size to ensure we have a safety margin.
        CRITICAL_THRESHOLD = 1.5 * gap
        
        # Search Threshold: If slack is above this, we can afford to 'waste' time 
        # searching for Spot instances (by returning NONE) to save money.
        SEARCH_THRESHOLD = 4.0 * gap

        # 1. Safety First: Critical Deadline Protection
        if slack < CRITICAL_THRESHOLD:
            # We are close to the wire. Must use On-Demand to guarantee progress.
            return ClusterType.ON_DEMAND

        # 2. Cost Optimization: Prefer Spot if available
        if has_spot:
            # Spot is available in current region and we have slack. Use it.
            return ClusterType.SPOT

        # 3. Spot Hunting Strategy
        # Spot is unavailable in current region. We should try another region.
        # Switch to the next region in a round-robin fashion.
        num_regions = self.env.get_num_regions()
        current_region_idx = self.env.get_current_region()
        next_region_idx = (current_region_idx + 1) % num_regions
        self.env.switch_region(next_region_idx)

        # Decide action in the new region
        # Note: We don't know has_spot for the new region yet.
        if slack > SEARCH_THRESHOLD:
            # High slack: Return NONE to pause execution. 
            # This costs $0 but burns 'gap' time. We hope to find Spot in the next step.
            return ClusterType.NONE
        else:
            # Moderate slack: We can't afford to waste more time searching.
            # Use On-Demand in the new region to ensure we make progress.
            return ClusterType.ON_DEMAND