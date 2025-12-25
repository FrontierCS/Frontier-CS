import json
from argparse import Namespace
from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType

class Solution(MultiRegionStrategy):
    """Adaptive multi-region scheduling strategy."""

    NAME = "adaptive_cost_optimizer"

    def solve(self, spec_path: str) -> "Solution":
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
        elapsed = self.env.elapsed_seconds
        done_work = sum(self.task_done_time)
        total_work = self.task_duration
        remaining_work = total_work - done_work
        
        if remaining_work <= 1e-6:
            return ClusterType.NONE
            
        time_remaining = self.deadline - elapsed
        gap = self.env.gap_seconds
        overhead = self.restart_overhead
        
        safe_buffer = overhead + 2.5 * gap
        must_start_threshold = remaining_work + safe_buffer
        
        is_panic = time_remaining < must_start_threshold
        
        if is_panic:
            if has_spot:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND
        
        if has_spot:
            return ClusterType.SPOT
        else:
            current_region = self.env.get_current_region()
            num_regions = self.env.get_num_regions()
            
            next_region = (current_region + 1) % num_regions
            self.env.switch_region(next_region)
            
            return ClusterType.NONE
