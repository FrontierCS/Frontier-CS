import json
from argparse import Namespace
import collections

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "my_strategy"

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

        self.num_regions = len(config['trace_files'])
        
        # Hyperparameters tuned for the problem's cost and time constraints.
        self.HISTORY_LEN = 24
        self.CONSECUTIVE_DOWN_THRESHOLD = 3
        self.SWITCH_SCORE_IMPROVEMENT = 0.2
        self.SLACK_FAILURES_BUFFER = 2

        # State tracking for each region.
        # Start optimistically, assuming all regions have good availability.
        self.spot_availability_history = [
            collections.deque([True] * self.HISTORY_LEN, maxlen=self.HISTORY_LEN)
            for _ in range(self.num_regions)
        ]
        self.consecutive_spot_down = [0] * self.num_regions
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # 1. Calculate current progress and time remaining.
        progress = sum(self.task_done_time)
        remaining_work = self.task_duration - progress

        if remaining_work <= 0:
            return ClusterType.NONE

        time_to_deadline = self.deadline - self.env.elapsed_seconds

        # 2. Update historical data for the current region.
        current_region = self.env.get_current_region()
        self.spot_availability_history[current_region].append(has_spot)
        
        if has_spot:
            self.consecutive_spot_down[current_region] = 0
        else:
            self.consecutive_spot_down[current_region] += 1
        
        # Reset consecutive down counters for other regions as they are not being observed.
        for i in range(self.num_regions):
            if i != current_region:
                self.consecutive_spot_down[i] = 0

        # 3. Crisis Mode: Check if we are approaching the deadline.
        # Calculate the time needed to finish if we attempt Spot now and it fails.
        # This is the point-of-no-return for trying Spot.
        worst_case_finish_time = remaining_work + self.restart_overhead + self.env.gap_seconds
        
        if time_to_deadline <= worst_case_finish_time:
            # Not enough time to risk a Spot failure; must use On-Demand.
            return ClusterType.ON_DEMAND

        # 4. Normal Mode: There is enough slack time.
        if has_spot:
            # Spot is available and cheap, the best choice when not in crisis.
            return ClusterType.SPOT
        else:
            # Spot is not available. Decide whether to switch regions, wait, or use On-Demand.
            
            # 4a. Region Switching Logic:
            # Consider switching only if Spot has been down for a while and another region looks better.
            if self.num_regions > 1 and self.consecutive_spot_down[current_region] >= self.CONSECUTIVE_DOWN_THRESHOLD:
                scores = [sum(h) / len(h) if h else 0.0 for h in self.spot_availability_history]
                current_score = scores[current_region]
                
                best_alt_score = -1.0
                best_alt_region = -1
                for i in range(self.num_regions):
                    if i != current_region and scores[i] > best_alt_score:
                        best_alt_score = scores[i]
                        best_alt_region = i

                if best_alt_region != -1 and best_alt_score > current_score + self.SWITCH_SCORE_IMPROVEMENT:
                    # A significantly better region exists, switch to it.
                    self.env.switch_region(best_alt_region)
                    # After switching, wait one step to observe the new region's availability.
                    return ClusterType.NONE

            # 4b. Stay-in-Region Logic (no switch occurred):
            # Decide between using expensive On-Demand or waiting (NONE).
            # This is a trade-off between cost and using up time slack.
            on_demand_finish_time = remaining_work + self.remaining_restart_overhead
            slack_time = time_to_deadline - on_demand_finish_time

            # Define a slack threshold based on surviving a few potential failures.
            slack_threshold = self.SLACK_FAILURES_BUFFER * (self.restart_overhead + self.env.gap_seconds)

            if slack_time < slack_threshold:
                # Slack is running low; must make progress using On-Demand.
                return ClusterType.ON_DEMAND
            else:
                # Plenty of slack; wait for Spot to become available again to save cost.
                return ClusterType.NONE