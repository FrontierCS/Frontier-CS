import json
import collections
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """
    An adaptive multi-region scheduling strategy that prioritizes Spot instances
    while maintaining a safety slack to ensure deadline compliance.
    """
    NAME = "AdaptiveSlackStrategy"

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

        num_regions = self.env.get_num_regions()
        
        self.history_window_size = 12
        self.spot_history = {
            i: collections.deque(maxlen=self.history_window_size)
            for i in range(num_regions)
        }
        self.visits = [0] * num_regions
        
        self.consecutive_spot_failures = 0

        self.switch_failure_threshold = 3
        
        self.initial_slack = self.deadline - self.task_duration
        self.wait_slack_fraction = 0.6
        
        self.is_initialized = False

        return self

    def _initialize_runtime_params(self):
        self.critical_slack_buffer = self.restart_overhead + self.env.gap_seconds
        self.wait_slack_threshold = self.initial_slack * self.wait_slack_fraction
        self.is_initialized = True

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not self.is_initialized:
            self._initialize_runtime_params()

        current_region = self.env.get_current_region()
        self.visits[current_region] += 1
        self.spot_history[current_region].append(1 if has_spot else 0)

        if has_spot:
            self.consecutive_spot_failures = 0
        else:
            self.consecutive_spot_failures += 1

        if (not has_spot and 
            self.consecutive_spot_failures >= self.switch_failure_threshold):
            num_regions = self.env.get_num_regions()
            scores = [0.0] * num_regions
            
            for i in range(num_regions):
                if self.visits[i] == 0:
                    scores[i] = 1.0
                else:
                    history = self.spot_history[i]
                    if len(history) > 0:
                        scores[i] = sum(history) / len(history)
            
            current_score = scores[current_region]
            scores[current_region] = -1.0 
            best_alternative_region = max(range(num_regions), key=lambda i: scores[i])

            if scores[best_alternative_region] > current_score:
                self.env.switch_region(best_alternative_region)
                self.consecutive_spot_failures = 0

        work_done = sum(self.task_done_time)
        remaining_work = self.task_duration - work_done
        
        if remaining_work <= 0:
            return ClusterType.NONE

        time_to_deadline = self.deadline - self.env.elapsed_seconds
        current_slack = time_to_deadline - remaining_work
        
        if current_slack <= self.critical_slack_buffer:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT
        else:
            if current_slack > self.wait_slack_threshold:
                return ClusterType.NONE
            else:
                return ClusterType.ON_DEMAND
