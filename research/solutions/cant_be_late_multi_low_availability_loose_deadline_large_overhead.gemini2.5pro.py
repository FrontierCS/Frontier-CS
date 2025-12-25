import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """
    A multi-region scheduling strategy that aims to minimize cost while ensuring
    task completion before the deadline.

    The strategy is based on a heuristic that uses full knowledge of future
    spot availability from trace files.

    Core Logic:
    1.  Pre-computation: In the `solve` method, load all spot availability traces
        and pre-compute a lookup table (`next_spot_timestep`) that gives the next
        available spot timestep for any given time and region.

    2.  Criticality Check: At each step, calculate the "slack time" - the amount
        of spare time available before the deadline, assuming all remaining work is
        done on reliable on-demand instances. If this slack is below a safety
        threshold (e.g., 1.5x the restart overhead), the strategy enters a
        "danger zone" and exclusively uses ON_DEMAND to guarantee progress.

    3.  Cost-driven Decisions (if not in danger zone):
        - If spot is available in the current region, use it (it's the cheapest).
        - If spot is not available, evaluate the options:
          a) Use ON_DEMAND in the current region.
          b) Wait (NONE) for a spot to become available in the current region.
          c) Switch to another region to find a spot.

    4.  Optimal Spot-Chasing: To decide between these options, the strategy
        calculates the minimum time required to get the next spot instance,
        considering all regions and including the time cost of switching
        (restart overhead) and waiting. Let this be `min_time_to_spot`.

    5.  Final Decision: The strategy compares the available `slack_time` with
        the `min_time_to_spot`.
        - If `slack_time` is safely larger than `min_time_to_spot` (i.e., we can
          afford the time cost of chasing the spot plus a buffer for a potential
          preemption), it executes the optimal spot-chasing plan (either switching
          or waiting).
        - Otherwise, it's too risky to wait or switch, so it uses ON_DEMAND to
          make immediate progress.
    """
    NAME = "my_strategy"  # REQUIRED: unique identifier

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the solution from spec_path config and perform pre-computation.
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

        self.spot_availability = []
        if "trace_files" in config:
            for trace_file in config["trace_files"]:
                with open(trace_file) as f:
                    self.spot_availability.append([bool(x) for x in json.load(f)])

        if not self.spot_availability:
            # This case should not happen in the evaluation based on the problem description.
            # Handle gracefully by assuming no spot is ever available.
            max_steps = int(self.deadline // self.env.gap_seconds) + 1 if self.env.gap_seconds > 0 else 1
            # Assuming a max of 8 regions if not specified
            num_regions_guess = len(config.get("trace_files", [])) or 8
            self.spot_availability = [[False] * max_steps for _ in range(num_regions_guess)]

        num_regions = len(self.spot_availability)
        num_timesteps = len(self.spot_availability[0]) if num_regions > 0 else 0

        self.next_spot_timestep = [[float('inf')] * (num_timesteps + 1) for _ in range(num_regions)]

        for r in range(num_regions):
            next_t = float('inf')
            for t in range(num_timesteps - 1, -1, -1):
                if self.spot_availability[r][t]:
                    next_t = t
                self.next_spot_timestep[r][t] = next_t
        
        self.DANGER_SLACK_FACTOR = 1.5
        self.CHASE_SPOT_SLACK_FACTOR = 1.0

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state using pre-computed data.
        """
        if self.env.gap_seconds == 0:
            current_t_step = 0
        else:
            current_t_step = int(self.env.elapsed_seconds // self.env.gap_seconds)

        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done

        if work_remaining <= 0:
            return ClusterType.NONE

        time_to_deadline = self.deadline - self.env.elapsed_seconds
        slack_time = time_to_deadline - work_remaining

        required_slack_for_risk = self.DANGER_SLACK_FACTOR * self.restart_overhead
        if slack_time < required_slack_for_risk:
            return ClusterType.ON_DEMAND

        current_region = self.env.get_current_region()
        if has_spot:
            return ClusterType.SPOT

        best_target_region = -1
        min_time_to_spot = float('inf')
        num_regions = self.env.get_num_regions()
        
        max_timesteps = len(self.spot_availability[0]) if num_regions > 0 else 0
        if current_t_step >= max_timesteps:
            return ClusterType.ON_DEMAND

        for r in range(num_regions):
            switch_overhead = 0 if r == current_region else self.restart_overhead
            
            next_spot_t = self.next_spot_timestep[r][current_t_step]
            if next_spot_t == float('inf'):
                continue

            wait_time = (next_spot_t - current_t_step) * self.env.gap_seconds
            total_time_cost = switch_overhead + wait_time
            
            if total_time_cost < min_time_to_spot:
                min_time_to_spot = total_time_cost
                best_target_region = r

        if best_target_region == -1:
            return ClusterType.ON_DEMAND

        required_slack_to_chase_spot = min_time_to_spot + self.CHASE_SPOT_SLACK_FACTOR * self.restart_overhead
        
        if slack_time > required_slack_to_chase_spot:
            if best_target_region == current_region:
                return ClusterType.NONE
            else:
                self.env.switch_region(best_target_region)
                if self.spot_availability[best_target_region][current_t_step]:
                    return ClusterType.SPOT
                else:
                    return ClusterType.NONE
        else:
            return ClusterType.ON_DEMAND
