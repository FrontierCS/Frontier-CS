import json
from argparse import Namespace
import math

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """
    A multi-region scheduling strategy that leverages perfect foresight of spot availability
    from trace files to make cost-effective decisions while ensuring the job finishes
    before the deadline.
    """
    NAME = "foresight_scheduler"

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the solution from spec_path config.

        This method loads the problem specification, initializes the base strategy,
        and most importantly, pre-processes the spot availability trace files.
        It reads all trace files to gain perfect foresight and computes the length
        of consecutive spot availability for each timestep in each region, which is
        key for the `_step` logic.
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

        # Pre-process trace files for spot availability foresight
        self.spot_availability = []
        if "trace_files" in config and config["trace_files"]:
            for trace_file in config["trace_files"]:
                with open(trace_file) as f:
                    trace_data = f.read().strip()
                    self.spot_availability.append([c == '1' for c in trace_data])

        # Pre-calculate consecutive spot availability runs for efficient lookup
        num_regions = len(self.spot_availability)
        if num_regions > 0:
            # Assuming all traces have the same length
            num_timesteps = len(self.spot_availability[0])
            self.consecutive_spot = [[0] * num_timesteps for _ in range(num_regions)]
            for r in range(num_regions):
                consecutive = 0
                for t in reversed(range(num_timesteps)):
                    if self.spot_availability[r][t]:
                        consecutive += 1
                    else:
                        consecutive = 0
                    self.consecutive_spot[r][t] = consecutive
        else:
            self.consecutive_spot = []

        # Heuristic parameters
        self.urgent_slack_threshold_h = 12.0
        self.wait_slack_threshold_h = 20.0

        # Known prices for cost-benefit analysis
        self.od_price = 3.06
        self.spot_price = 0.9701
        if self.od_price > self.spot_price:
            self.price_ratio_od_over_savings = self.od_price / (self.od_price - self.spot_price)
        else:
            self.price_ratio_od_over_savings = float('inf')

        # One-time initialization cache
        self.cost_based_switch_threshold = None

        return self

    def _find_best_switch_target(self, current_timestep: int, current_region: int):
        """Helper to find the best region to switch to."""
        num_regions = self.env.get_num_regions()
        candidates = []
        if self.spot_availability and current_timestep < len(self.spot_availability[0]):
            for r in range(num_regions):
                if r == current_region:
                    continue
                if self.spot_availability[r][current_timestep]:
                    run_length = self.consecutive_spot[r][current_timestep]
                    candidates.append((run_length, r))
        
        if not candidates:
            return 0, -1

        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0]

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        # One-time initialization for values that depend on self.env
        if self.cost_based_switch_threshold is None:
            if self.env.gap_seconds > 0:
                self.cost_based_switch_threshold = (
                    (self.restart_overhead / self.env.gap_seconds) *
                    self.price_ratio_od_over_savings
                )
            else:
                self.cost_based_switch_threshold = float('inf')

        # --- Step 1: Check for task completion ---
        work_done = sum(self.task_done_time)
        if work_done >= self.task_duration:
            return ClusterType.NONE

        # --- Step 2: Panic Mode ---
        work_remaining = self.task_duration - work_done
        time_for_work = self.deadline - self.env.elapsed_seconds - self.remaining_restart_overhead
        if work_remaining >= time_for_work:
            return ClusterType.ON_DEMAND

        # --- Step 3: Main Decision Logic ---
        current_timestep = int(self.env.elapsed_seconds // self.env.gap_seconds)
        current_region = self.env.get_current_region()

        # Fallback if past the end of trace data
        if not self.spot_availability or current_timestep >= len(self.spot_availability[0]):
            if has_spot:
                return ClusterType.SPOT
            slack = time_for_work - work_remaining
            if slack > self.urgent_slack_threshold_h * 3600:
                return ClusterType.NONE
            else:
                return ClusterType.ON_DEMAND

        # If spot is available in the current region, use it.
        if has_spot:
            return ClusterType.SPOT

        # Spot is not available locally. Consider switching or waiting.
        slack = time_for_work - work_remaining

        # If slack is very high, just wait to save costs.
        if slack > self.wait_slack_threshold_h * 3600:
            return ClusterType.NONE
        
        # Slack is moderate, try to make progress cost-effectively.
        best_run, best_region = self._find_best_switch_target(current_timestep, current_region)

        # If a switch is cost-effective, take it.
        if best_region != -1 and best_run > self.cost_based_switch_threshold:
            self.env.switch_region(best_region)
            return ClusterType.SPOT

        # No good switch found. Fallback to ON_DEMAND or NONE based on urgency.
        if slack > self.urgent_slack_threshold_h * 3600:
            return ClusterType.NONE
        else:
            return ClusterType.ON_DEMAND
