import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

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
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        # Get current simulation state
        elapsed = self.env.elapsed_seconds
        work_done = sum(self.task_done_time)
        work_rem = self.task_duration - work_done
        time_rem = self.deadline - elapsed
        
        # Get parameters
        overhead = self.restart_overhead
        # Use a default gap if not available, though env.gap_seconds should be set
        gap = getattr(self.env, "gap_seconds", 300.0)
        
        # Calculate Safety Threshold
        # We need to guarantee completion on On-Demand (OD).
        # We must switch to OD if: time_rem <= work_rem + overhead + buffer
        # Overhead: Required if we are not currently OD (or to be safe).
        # Buffer: Account for discrete timesteps (gap) and float precision. 
        # We use 2 * gap to be robust.
        safety_threshold = overhead + (2.0 * gap)
        
        # Panic Mode Check
        # If the remaining slack is below our safety threshold, force On-Demand.
        # This ensures we don't miss the hard deadline (-100,000 penalty).
        if time_rem <= (work_rem + safety_threshold):
            return ClusterType.ON_DEMAND

        # Slack Mode
        # We have enough time to try Spot instances or switch regions.

        # 1. If Spot is available in the current region, use it.
        if has_spot:
            return ClusterType.SPOT
            
        # 2. If Spot is NOT available in the current region, switch region.
        # Switching incurs 'overhead', but since we passed the panic check,
        # we have enough slack to pay this cost in hopes of finding cheap Spot.
        num_regions = self.env.get_num_regions()
        if num_regions > 1:
            curr_region = self.env.get_current_region()
            # Round-robin switching ensures we eventually check all regions
            next_region = (curr_region + 1) % num_regions
            self.env.switch_region(next_region)
            # We intend to use Spot in the new region
            return ClusterType.SPOT
            
        # 3. Fallback: Single region and no Spot.
        # We must make progress.
        return ClusterType.ON_DEMAND