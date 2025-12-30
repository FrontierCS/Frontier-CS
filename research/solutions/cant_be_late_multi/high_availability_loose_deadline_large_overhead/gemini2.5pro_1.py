import json
from argparse import Namespace
import numpy as np

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """
    A multi-region scheduling strategy that uses lookahead on spot traces
    to make decisions.

    The core idea is to:
    1. Prioritize meeting the deadline. If time is running out, switch to
       reliable On-Demand instances.
    2. Otherwise, try to use cheap Spot instances.
    3. Use pre-processed spot availability traces to predict future
       stability of each region.
    4. Stay in the current region if it's stable enough, or switch to a
       more stable region if the benefit outweighs the switching cost.
    5. If no Spot instances are available anywhere, decide whether to wait
       (if there's enough slack time) or use On-Demand to guarantee progress.
    """

    NAME = "LookaheadSpotSelector"

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

        self.LOOKAHEAD_WINDOW = 10
        self.SWITCH_SCORE_THRESHOLD = 2
        self.WAIT_SLACK_MULTIPLIER = 5

        self.trace_files = config.get("trace_files", [])
        self.num_regions = len(self.trace_files)
        self.spot_availability = []
        for trace_file in self.trace_files:
            with open(trace_file) as f:
                trace_data = json.load(f)
                self.spot_availability.append(np.array(trace_data, dtype=bool))
        
        if not self.spot_availability or len(self.spot_availability[0]) == 0:
            self.num_timesteps = 0
            self.spot_scores = np.array([[] for _ in range(self.num_regions)])
            return self
        
        self.num_timesteps = len(self.spot_availability[0])

        self.spot_scores = np.zeros((self.num_regions, self.num_timesteps), dtype=np.int32)
        for r in range(self.num_regions):
            end_idx = min(self.LOOKAHEAD_WINDOW, self.num_timesteps)
            current_sum = np.sum(self.spot_availability[r][0:end_idx])
            self.spot_scores[r, 0] = current_sum

            for t in range(1, self.num_timesteps):
                current_sum -= self.spot_availability[r][t - 1]
                if t + self.LOOKAHEAD_WINDOW - 1 < self.num_timesteps:
                    current_sum += self.spot_availability[r][t + self.LOOKAHEAD_WINDOW - 1]
                self.spot_scores[r, t] = current_sum

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        work_done = sum(self.task_done_time)
        work_rem = self.task_duration - work_done
        if work_rem <= 1e-9:
            return ClusterType.NONE

        if self.env.gap_seconds > 0:
            time_step_idx = int(self.env.elapsed_seconds / self.env.gap_seconds)
        else:
            time_step_idx = 0

        if time_step_idx >= self.num_timesteps:
            return ClusterType.ON_DEMAND

        time_rem = self.deadline - self.env.elapsed_seconds
        
        time_needed_od = work_rem + self.restart_overhead
        if time_rem <= time_needed_od + self.env.gap_seconds:
            return ClusterType.ON_DEMAND

        current_region = self.env.get_current_region()
        
        best_current_score = -1
        best_current_region = -1
        if self.num_regions > 0:
            for r in range(self.num_regions):
                if self.spot_availability[r][time_step_idx]:
                    score = self.spot_scores[r, time_step_idx]
                    if score > best_current_score:
                        best_current_score = score
                        best_current_region = r
        
        if has_spot:
            current_score = self.spot_scores[current_region, time_step_idx]
            
            if (best_current_region != -1 and
                best_current_region != current_region and
                best_current_score > current_score + self.SWITCH_SCORE_THRESHOLD):
                self.env.switch_region(best_current_region)
                return ClusterType.SPOT
            else:
                return ClusterType.SPOT
        else:
            if best_current_region != -1:
                self.env.switch_region(best_current_region)
                return ClusterType.SPOT
            else:
                slack = time_rem - work_rem
                wait_threshold = self.WAIT_SLACK_MULTIPLIER * self.restart_overhead
                
                if slack > wait_threshold and last_cluster_type != ClusterType.NONE:
                    return ClusterType.NONE
                else:
                    return ClusterType.ON_DEMAND