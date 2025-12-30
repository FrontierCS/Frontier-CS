import json
from argparse import Namespace
import math

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "cant_be_late_v3"  # REQUIRED: unique identifier

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

        self.num_regions = self.env.get_num_regions()
        self.spot_stats = [{'seen': 0, 'available': 0} for _ in range(self.num_regions)]

        self.SAFETY_FACTOR = 1.2
        self.WAIT_FACTOR = 1.8
        self.P_SWITCH_THRESH = 0.4
        self.EXPLORATION_STEPS_PER_REGION = 2
        
        self.total_exploration_steps = self.num_regions * self.EXPLORATION_STEPS_PER_REGION

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        current_region = self.env.get_current_region()
        
        self.spot_stats[current_region]['seen'] += 1
        if has_spot:
            self.spot_stats[current_region]['available'] += 1

        remaining_work = self.task_duration - sum(self.task_done_time)
        if remaining_work <= 1e-6:
            return ClusterType.NONE

        total_steps_so_far = int(round(self.env.elapsed_seconds / self.env.gap_seconds))
        
        if total_steps_so_far < self.total_exploration_steps:
            target_region_idx = total_steps_so_far // self.EXPLORATION_STEPS_PER_REGION
            target_region = target_region_idx % self.num_regions

            if current_region != target_region:
                self.env.switch_region(target_region)
                return ClusterType.ON_DEMAND
            
            if has_spot:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND
        
        time_to_deadline = self.deadline - self.env.elapsed_seconds
        
        time_ratio = time_to_deadline / (remaining_work + 1e-9)

        if time_ratio <= self.SAFETY_FACTOR:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT
            
        probs = [
            (s['available'] + 1.0) / (s['seen'] + 2.0) for s in self.spot_stats
        ]
        
        best_region_idx, best_prob = max(enumerate(probs), key=lambda item: item[1])
        
        if best_prob > self.P_SWITCH_THRESH and best_region_idx != current_region:
            self.env.switch_region(best_region_idx)
            return ClusterType.ON_DEMAND
        
        if time_ratio <= self.WAIT_FACTOR:
            return ClusterType.ON_DEMAND
        else:
            return ClusterType.NONE