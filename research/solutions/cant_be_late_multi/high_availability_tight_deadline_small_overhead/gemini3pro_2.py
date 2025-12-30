import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "AdaptiveSlackStrategy"

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
        Strategy:
        1. Calculate 'slack': Time Remaining - (Work Remaining + Overhead).
        2. If slack is CRITICAL (low): Force On-Demand to ensure completion.
        3. If slack is HIGH and Spot is missing: Pause (NONE) and switch region to find Spot (save money).
        4. If slack is MEDIUM and Spot is missing: Run On-Demand and switch region (buy time while searching).
        5. If Spot is available: Use Spot (unless Critical).
        """
        # --- 1. Gather State ---
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        gap = self.env.gap_seconds
        elapsed = self.env.elapsed_seconds
        
        work_done = sum(self.task_done_time)
        remaining_work = self.task_duration - work_done
        time_left = self.deadline - elapsed
        overhead = self.restart_overhead
        
        # --- 2. Calculate Slack ---
        # Conservative estimate of time required to finish via safe path (On-Demand)
        # We add overhead to account for potential restart if we are currently Stopped or need to switch.
        required_time = remaining_work + overhead
        slack = time_left - required_time
        
        # --- 3. Define Thresholds ---
        # Critical Threshold: If slack falls below this, we are at risk of missing the deadline
        # if we incur any more interruptions (like Spot preemption).
        # We define this as 2 steps (gaps) to be safe against one failure + overhead.
        CRITICAL_THRESHOLD = 2.0 * gap
        
        # Probe Threshold: If slack is above this, we can afford to 'waste' time steps 
        # (return NONE) to search for a region with Spot instances, saving money.
        # We keep a substantial buffer (6 steps) to ensure we transition to OD fallback safely.
        PROBE_THRESHOLD = 6.0 * gap

        # --- 4. Decision Logic ---
        
        # Case A: Spot is available in current region
        if has_spot:
            # If we are critically low on time, On-Demand is safer because it cannot be preempted.
            if slack < CRITICAL_THRESHOLD:
                return ClusterType.ON_DEMAND
            # Otherwise, capitalize on cheap Spot instances.
            return ClusterType.SPOT
            
        # Case B: Spot is NOT available in current region
        else:
            # If we are critically low on time, we must ensure progress.
            # We stay in the current region and use On-Demand to avoid any potential
            # extra complications or overheads from switching (though overheads don't stack,
            # switching logic is unnecessary risk here).
            if slack < CRITICAL_THRESHOLD:
                return ClusterType.ON_DEMAND
            
            # If we have slack, we must switch regions to try and find Spot availability.
            # Strategy: Simple cyclic search.
            next_region = (current_region + 1) % num_regions
            self.env.switch_region(next_region)
            
            # Now decide whether to work (OD) or wait (NONE) in this new region for the current step.
            
            if slack > PROBE_THRESHOLD:
                # High slack: Return NONE. We lose 1 step of time, but pay $0.
                # In the next step, we will check if the new region has Spot.
                return ClusterType.NONE
            else:
                # Medium slack: We want to search, but we also need to chip away at the work.
                # Return ON_DEMAND. We pay OD price, but we make progress.
                # In the next step, if the new region has Spot, we can switch to it.
                return ClusterType.ON_DEMAND