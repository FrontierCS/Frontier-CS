import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Adaptive multi-region scheduling strategy."""

    NAME = "adaptive_region_hopper"

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
        """
        # 1. Calculate current state
        done_work = sum(self.task_done_time)
        remaining_work = self.task_duration - done_work
        
        # If task finished (should be handled by env, but for safety)
        if remaining_work <= 1e-6:
            return ClusterType.NONE

        elapsed = self.env.elapsed_seconds
        deadline = self.deadline
        time_left = deadline - elapsed
        
        gap = self.env.gap_seconds
        overhead = self.restart_overhead
        
        # 2. Define Thresholds
        
        # Critical Threshold:
        # If remaining time is close to the bare minimum needed (work + overhead),
        # we must use On-Demand to guarantee completion.
        # We add a buffer of 2 steps to account for any jitter or precise timing issues.
        force_od_threshold = remaining_work + overhead + (2.0 * gap)
        
        # Search Threshold:
        # If Spot is unavailable, we might want to switch regions to find it.
        # Switching and pausing (NONE) costs 1 gap of time.
        # We can only afford this if we still have enough time to finish safely afterwards.
        # We require at least 'force_od_threshold' + 1 gap to attempt a search.
        can_search_threshold = force_od_threshold + gap

        # 3. Decision Logic

        # PRIORITY 1: Ensure Deadline (Safety)
        if time_left < force_od_threshold:
            # Not enough slack to risk Spot interruptions or searching. Force OD.
            return ClusterType.ON_DEMAND

        # PRIORITY 2: Minimize Cost (Use Spot if available)
        if has_spot:
            # Spot is available in current region and we have slack. Use it.
            return ClusterType.SPOT

        # PRIORITY 3: Search for Spot (Multi-region switching)
        if time_left > can_search_threshold:
            # Spot is unavailable here, but we have plenty of slack.
            # Switch to next region and return NONE to probe availability in the next step.
            # (Returning SPOT immediately after switch is unsafe as we don't know new region's status)
            
            num_regions = self.env.get_num_regions()
            current_region_idx = self.env.get_current_region()
            next_region_idx = (current_region_idx + 1) % num_regions
            
            self.env.switch_region(next_region_idx)
            return ClusterType.NONE
        
        # PRIORITY 4: Intermediate Fallback
        # Spot unavailable, and not enough slack to waste time searching, 
        # but not critically close to deadline yet.
        # We must make progress now, so use OD.
        return ClusterType.ON_DEMAND