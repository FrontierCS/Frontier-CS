import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "CostOptimizedStrategy"

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
        
        # State to track region hunting
        self.consecutive_failures = 0
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        elapsed = self.env.elapsed_seconds
        done = sum(self.task_done_time)
        
        # Calculate remaining work needed, including any currently pending overhead
        pending_overhead = self.remaining_restart_overhead
        needed = self.task_duration - done + pending_overhead
        
        remaining_time = self.deadline - elapsed
        gap = self.env.gap_seconds
        overhead = self.restart_overhead
        
        # 1. Critical Deadline Safety Check
        # If we attempt Spot and get preempted (or fail), we lose 'gap' seconds effectively
        # (time advances, work doesn't). We also incur 'overhead' to restart.
        # We must ensure that even after such a failure, we have enough time to finish 
        # using On-Demand (which is assumed reliable).
        # Required buffer: time for one failure (gap) + restart (overhead) + remaining work (needed)
        # We add a small safety margin (5 minutes = 300s) for precision issues.
        spot_unsafe = remaining_time < (needed + gap + overhead + 300.0)
        
        if has_spot:
            # Spot is available in current region.
            self.consecutive_failures = 0 # Reset hunting counter
            
            if spot_unsafe:
                # Too risky to use Spot, deadline is too tight.
                return ClusterType.ON_DEMAND
            return ClusterType.SPOT
            
        # 2. No Spot in Current Region
        # We must decide whether to stay (use OD) or switch regions (hunt for Spot).
        
        # Panic Check: If time is tight, we cannot afford the overhead of switching regions
        # just to check for Spot. We must settle for OD in current region to maximize work time.
        # Threshold: Needed work + Overhead + Buffer (2 hours).
        panic_threshold = needed + overhead + (2.0 * 3600.0)
        is_panic = remaining_time < panic_threshold
        
        if is_panic:
            return ClusterType.ON_DEMAND
            
        # 3. Spot Hunting Logic
        # We are not in panic mode, so we should try to find Spot to save money.
        
        # To avoid infinite switching loops (paying overhead every step) if Spot is globally unavailable,
        # we track how many regions we've checked consecutively.
        num_regions = self.env.get_num_regions()
        
        if self.consecutive_failures >= num_regions:
            # We have cycled through all regions and found no Spot.
            # Stay in current region using OD for a few steps to make progress.
            # We periodically reset to try hunting again (every 3 steps after full cycle).
            self.consecutive_failures += 1
            if self.consecutive_failures > num_regions + 3:
                self.consecutive_failures = 0
            return ClusterType.ON_DEMAND

        # Switch to the next region to check availability.
        # We cannot return SPOT immediately because we don't know if the new region has Spot.
        # We return ON_DEMAND to ensure we do useful work during the probe step (at OD price),
        # rather than pausing (NONE) which wastes time.
        curr_region = self.env.get_current_region()
        next_region = (curr_region + 1) % num_regions
        self.env.switch_region(next_region)
        self.consecutive_failures += 1
        
        return ClusterType.ON_DEMAND