import json
import math
import os
from argparse import Namespace

try:
    from sky_spot.strategies.multi_strategy import MultiRegionStrategy
    from sky_spot.utils import ClusterType
except ImportError:
    # Dummy classes for standalone execution if the environment is not available.
    class ClusterType:
        SPOT = "SPOT"
        ON_DEMAND = "ON_DEMAND"
        NONE = "NONE"

    class MultiRegionStrategy:
        def __init__(self, args):
            self.args = args
            self.task_duration = args.task_duration_hours[0] * 3600
            self.deadline = args.deadline_hours * 3600
            self.restart_overhead = args.restart_overhead_hours[0] * 3600
            self.env = None

        def solve(self, spec_path: str):
            raise NotImplementedError

        def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
            raise NotImplementedError


class Solution(MultiRegionStrategy):
    """
    A multi-region scheduling strategy that aims to minimize cost by prioritizing
    spot instances while ensuring the job finishes before the deadline.

    Strategy Overview:
    1.  Pre-computation (`solve`): Load spot availability traces for all
        regions to enable informed, forward-looking decisions.
    2.  Panic Mode: At each step, calculate the minimum time required to
        finish the job using only on-demand instances. If the projected
        finish time is too close to the deadline, switch to on-demand
        unconditionally to guarantee completion. This acts as a safety net.
    3.  Spot Prioritization: If not in panic mode, prioritize spot instances.
        - If the current region has a spot instance available (`has_spot` is True),
          use it immediately. Switching regions incurs an overhead, so staying
          put is optimal if a cheap resource is available.
    4.  Proactive Region Switching: If the current region lacks a spot instance:
        - Search other regions for spot availability at the current time step using
          the pre-loaded trace data.
        - To select the best region among those with available spots, score
          them based on their spot availability in a short future window.
        - Switch to the best-scoring region and use its spot instance.
    5.  Cost-aware Waiting: If no region has a spot instance available:
        - Calculate the "slack" time remaining before panic mode is triggered.
        - If there is sufficient slack (more than one time step), choose to
          wait (`NONE`) to save costs, betting on a spot instance becoming
          available soon.
        - If slack is low, use an on-demand instance to guarantee progress and
          avoid falling behind schedule.
    """

    NAME = "Cant-Be-Late_Strategy"

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

        self.spot_availability = []
        base_dir = os.path.dirname(spec_path)
        for trace_file in config["trace_files"]:
            full_trace_path = os.path.join(base_dir, trace_file)
            if not os.path.isabs(trace_file):
                 full_trace_path = os.path.join(base_dir, trace_file)
            else:
                 full_trace_path = trace_file

            with open(full_trace_path) as f:
                trace = [int(line.strip()) for line in f]
                self.spot_availability.append(trace)

        # Hyperparameters for the strategy
        self.lookahead_window = 24
        self.safety_buffer_factor = 1.5

        return self

    def _estimate_time_to_finish_on_demand(self, work_remaining: float) -> float:
        """
        Calculates a conservative estimate of the time required to complete
        the remaining work using only on-demand instances.
        """
        if work_remaining <= 0:
            return 0

        gap = self.env.gap_seconds
        overhead = self.restart_overhead

        work_done_first_step = gap - overhead
        if work_done_first_step <= 0:
            return float('inf')

        if work_remaining <= work_done_first_step:
            return gap

        work_after_first_step = work_remaining - work_done_first_step
        num_subsequent_steps = math.ceil(work_after_first_step / gap)
        
        total_time = gap * (1 + num_subsequent_steps)
        return total_time

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done

        if work_remaining <= 0:
            return ClusterType.NONE

        current_time = self.env.elapsed_seconds
        current_step_idx = int(round(current_time / self.env.gap_seconds))

        # 1. PANIC MODE CHECK
        time_needed_od = self._estimate_time_to_finish_on_demand(work_remaining)
        safety_buffer = self.safety_buffer_factor * self.env.gap_seconds
        
        if current_time + time_needed_od >= self.deadline - safety_buffer:
            return ClusterType.ON_DEMAND

        # 2. IF SPOT IS AVAILABLE IN CURRENT REGION, USE IT
        if has_spot:
            return ClusterType.SPOT

        # 3. CURRENT REGION HAS NO SPOT, SEARCH FOR A BETTER ONE
        best_region = -1
        best_score = -1
        num_regions = self.env.get_num_regions()
        current_region = self.env.get_current_region()

        for r in range(num_regions):
            if r == current_region:
                continue
            
            trace_len = len(self.spot_availability[r])
            if current_step_idx < trace_len and self.spot_availability[r][current_step_idx] == 1:
                end_window = min(current_step_idx + self.lookahead_window, trace_len)
                score = sum(self.spot_availability[r][current_step_idx:end_window])
                if score > best_score:
                    best_score = score
                    best_region = r

        if best_region != -1:
            self.env.switch_region(best_region)
            return ClusterType.SPOT

        # 4. NO SPOT AVAILABLE ANYWHERE: WAIT OR USE ON-DEMAND
        panic_time = self.deadline - time_needed_od - safety_buffer
        slack = panic_time - current_time

        if slack > self.env.gap_seconds:
            return ClusterType.NONE
        else:
            return ClusterType.ON_DEMAND
