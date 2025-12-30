import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Adaptive multi-region scheduling strategy."""

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
        Strategically switches between Spot and On-Demand based on remaining slack time.
        """
        # Calculate work remaining
        done = sum(self.task_done_time)
        needed = self.task_duration - done
        
        # If task is effectively done, stop
        if needed <= 1e-6:
            return ClusterType.NONE

        elapsed = self.env.elapsed_seconds
        time_left = self.deadline - elapsed
        
        restart_oh = self.restart_overhead
        gap = self.env.gap_seconds
        
        # Calculate slack: Time available minus (work needed + one restart overhead penalty)
        # We include restart_oh in the "needed" baseline to be conservative about the final switch to OD.
        slack = time_left - (needed + restart_oh)
        
        # Critical Threshold Calculation:
        # We need a buffer to decide when to stop hunting for Spot instances and force On-Demand.
        # We set this to 2.0 * gap + restart_oh.
        # Logic: 
        # 1. We need at least 'gap' time to recover if a chosen Spot step fails or if we pause to switch regions.
        # 2. We use 2.0x to allow for a small "hunting" window where we might switch regions.
        # 3. If slack falls below this, the risk of missing the deadline outweighs cost savings.
        critical_threshold = 2.0 * gap + restart_oh

        # 1. Critical Mode: Insufficient slack -> Force On-Demand for reliability
        if slack < critical_threshold:
            return ClusterType.ON_DEMAND
            
        # 2. Economic Mode: Sufficient slack -> Prioritize Spot
        if has_spot:
            # Spot is available in the current region
            return ClusterType.SPOT
        else:
            # Spot is unavailable in current region, but we have slack.
            # Strategy: Switch to the next region and return NONE (pause).
            # We pay the cost of one time step (gap) to potentially find a Spot instance in the next region.
            num_regions = self.env.get_num_regions()
            current_region = self.env.get_current_region()
            next_region = (current_region + 1) % num_regions
            
            self.env.switch_region(next_region)
            return ClusterType.NONE