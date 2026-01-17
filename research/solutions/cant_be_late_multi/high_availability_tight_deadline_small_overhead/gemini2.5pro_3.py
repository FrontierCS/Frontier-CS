import json
import math
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """
    A multi-region scheduling strategy that uses pre-computed trace information
    to make informed decisions. The strategy is based on a primary "urgency check"
    to ensure the deadline is met, and heuristics for region and cluster selection
    to minimize cost when there is sufficient time slack.
    """

    NAME = "CantBeLate"

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the solution from spec_path config.

        This method pre-loads spot availability traces and computes a lookup table
        for future spot availability, which is used by the stepping logic.
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

        self.spot_traces = []
        if "trace_files" in config and config["trace_files"]:
            for trace_file in config["trace_files"]:
                try:
                    with open(trace_file) as f:
                        self.spot_traces.append([bool(int(x)) for x in f.read().splitlines()])
                except (IOError, ValueError):
                    self.spot_traces.append([])

        self.num_regions = len(self.spot_traces)
        self.num_steps = 0
        if self.num_regions > 0 and self.spot_traces and self.spot_traces[0]:
            self.num_steps = len(self.spot_traces[0])
        
        self.spot_price_per_hour = 0.9701
        self.ondemand_price_per_hour = 3.06
        if self.env and self.env.gap_seconds > 0:
            self.spot_price = self.spot_price_per_hour * self.env.gap_seconds / 3600.0
            self.ondemand_price = self.ondemand_price_per_hour * self.env.gap_seconds / 3600.0
        else:
            self.spot_price = 0.0
            self.ondemand_price = 0.0

        self.future_spot_steps = [[0] * (self.num_steps + 1) for _ in range(self.num_regions)]
        if self.num_regions > 0:
            for r in range(self.num_regions):
                if not self.spot_traces[r]: continue
                for t in range(self.num_steps - 1, -1, -1):
                    self.future_spot_steps[r][t] = int(self.spot_traces[r][t]) + self.future_spot_steps[r][t + 1]

        self.safety_buffer_time = self.restart_overhead

        if self.ondemand_price > self.spot_price and self.env and self.env.gap_seconds > 0:
            price_ratio = self.ondemand_price / (self.ondemand_price - self.spot_price)
            overhead_in_steps = self.restart_overhead / self.env.gap_seconds
            self.region_switch_threshold = price_ratio * overhead_in_steps
        else:
            self.region_switch_threshold = float('inf')

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide the next action based on a three-stage heuristic:
        1. Urgency Check: If finishing on time is at risk, switch to On-Demand.
        2. Region Selection: If not urgent, pick the region with the best future spot prospects.
        3. Cluster Selection: In the chosen region, use Spot if available. If not, decide
           whether to wait (NONE) or use On-Demand based on available time slack.
        """
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        if work_remaining <= 1e-9:
            return ClusterType.NONE

        if not (self.env and self.env.gap_seconds > 0 and self.num_regions > 0):
            return ClusterType.ON_DEMAND

        elapsed_time = self.env.elapsed_seconds
        time_to_deadline = self.deadline - elapsed_time
        current_step = int(elapsed_time / self.env.gap_seconds)

        # 1. URGENCY CHECK (Point of No Return)
        time_needed_on_demand = self.restart_overhead + work_remaining

        if time_to_deadline <= time_needed_on_demand + self.safety_buffer_time:
            return ClusterType.ON_DEMAND
        
        if current_step >= self.num_steps:
            return ClusterType.ON_DEMAND

        # 2. REGION SELECTION
        current_region = self.env.get_current_region()
        
        region_scores = [self.future_spot_steps[r][current_step] for r in range(self.num_regions)]
        best_region = max(range(self.num_regions), key=lambda r: region_scores[r])
        
        if best_region != current_region:
            current_score = region_scores[current_region]
            best_score = region_scores[best_region]
            if best_score > current_score + self.region_switch_threshold:
                self.env.switch_region(best_region)
                current_region = best_region

        # 3. CLUSTER SELECTION
        has_spot_in_chosen_region = self.spot_traces[current_region][current_step]
        
        if has_spot_in_chosen_region:
            return ClusterType.SPOT
        else:
            slack_time = time_to_deadline - work_remaining
            
            time_to_next_spot = float('inf')
            if current_step + 1 < self.num_steps:
                try:
                    offset = self.spot_traces[current_region][current_step + 1:].index(True)
                    time_to_next_spot = (offset + 1) * self.env.gap_seconds
                except ValueError:
                    pass

            if slack_time - time_to_next_spot < self.safety_buffer_time:
                return ClusterType.ON_DEMAND
            else:
                return ClusterType.NONE