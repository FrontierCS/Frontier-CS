import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args):
        super().__init__(args)
        self.deadline_cushion = None
        self.wait_cushion = None
        self.finish_up_threshold = None
        self.initialized = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _initialize_params(self):
        deadline_cushion_multiplier = 4
        wait_cushion_multiplier = 20
        finish_up_multiplier = 5

        self.deadline_cushion = deadline_cushion_multiplier * self.restart_overhead
        self.wait_cushion = wait_cushion_multiplier * self.restart_overhead
        self.finish_up_threshold = finish_up_multiplier * self.env.gap_seconds
        
        self.initialized = True

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not self.initialized:
            self._initialize_params()

        work_done = sum(end - start for start, end in self.task_done_time)
        work_remaining = self.task_duration - work_done

        if work_remaining <= 0:
            return ClusterType.NONE

        if work_remaining < self.finish_up_threshold:
            return ClusterType.ON_DEMAND

        time_to_deadline = self.deadline - self.env.elapsed_seconds
        
        current_slack = time_to_deadline - work_remaining
        
        if current_slack <= self.deadline_cushion:
            return ClusterType.ON_DEMAND
            
        if has_spot:
            return ClusterType.SPOT
        
        if current_slack <= self.wait_cushion:
            return ClusterType.ON_DEMAND
        else:
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser: argparse.ArgumentParser):
        args, _ = parser.parse_known_args()
        return cls(args)