import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """
    Your multi-region scheduling strategy.
    """
    NAME = "slack_guided_ewma_search"

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

        num_regions = self.env.get_num_regions()
        self.region_spot_scores = [1.0] * num_regions
        self.alpha = 0.1

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        current_region = self.env.get_current_region()
        current_score = self.region_spot_scores[current_region]
        observation = 1.0 if has_spot else 0.0
        new_score = self.alpha * observation + (1 - self.alpha) * current_score
        self.region_spot_scores[current_region] = new_score

        work_done = sum(self.task_done_time)
        remaining_work = self.task_duration - work_done

        if remaining_work <= 0:
            return ClusterType.NONE

        time_to_finish_on_demand = self.remaining_restart_overhead + remaining_work
        time_to_deadline = self.deadline - self.env.elapsed_seconds
        
        slack = time_to_deadline - time_to_finish_on_demand

        potential_loss_from_preemption = self.restart_overhead + self.env.gap_seconds
        time_cost_of_region_switch = self.restart_overhead
        
        safety_buffer = self.restart_overhead * 0.5

        if slack <= potential_loss_from_preemption + safety_buffer:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT
        else:
            if slack - time_cost_of_region_switch > potential_loss_from_preemption + safety_buffer:
                best_next_region = -1
                max_score = -1.0
                num_regions = self.env.get_num_regions()
                for i in range(num_regions):
                    if i == current_region:
                        continue
                    if self.region_spot_scores[i] > max_score:
                        max_score = self.region_spot_scores[i]
                        best_next_region = i
                
                if best_next_region != -1:
                    self.env.switch_region(best_next_region)
                    return ClusterType.NONE
                else:
                    return ClusterType.ON_DEMAND
            else:
                return ClusterType.ON_DEMAND