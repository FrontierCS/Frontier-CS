import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """
    A multi-region scheduling strategy that prioritizes cost-effective Spot instances
    while ensuring the task completes before the deadline.
    """
    NAME = "foresight_optimizer"

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

        # Load spot availability traces for all regions for perfect foresight.
        self.spot_traces = []
        if 'trace_files' in config:
            for trace_file in config["trace_files"]:
                try:
                    with open(trace_file) as f:
                        # Assumes trace file has '1' for available, otherwise unavailable.
                        # Ignores empty lines.
                        trace = [line.strip() == '1' for line in f if line.strip()]
                        self.spot_traces.append(trace)
                except FileNotFoundError:
                    # In case a trace file is not found, assume no spot availability.
                    self.spot_traces.append([])
        
        # Caching for performance optimization on summing work done.
        self.cached_work_done = 0.0
        self.cached_task_done_len = 0

        return self

    def get_spot_availability(self, region_idx: int, time_step: int) -> bool:
        """Safely gets spot availability from pre-loaded trace data."""
        if region_idx < len(self.spot_traces) and time_step < len(self.spot_traces[region_idx]):
            return self.spot_traces[region_idx][time_step]
        return False

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        # Optimized calculation of cumulative work done to avoid O(N^2) complexity.
        if len(self.task_done_time) > self.cached_task_done_len:
            new_work = sum(self.task_done_time[self.cached_task_done_len:])
            self.cached_work_done += new_work
            self.cached_task_done_len = len(self.task_done_time)
        elif len(self.task_done_time) < self.cached_task_done_len:
            # List has been reset or shrunk, re-calculate from scratch.
            self.cached_work_done = sum(self.task_done_time)
            self.cached_task_done_len = len(self.task_done_time)
        
        work_done = self.cached_work_done
        work_remaining = self.task_duration - work_done

        # 1. If task is finished, do nothing to save cost.
        if work_remaining <= 0:
            return ClusterType.NONE

        elapsed_seconds = self.env.elapsed_seconds
        current_time_step = int(elapsed_seconds / self.env.gap_seconds)
        time_to_deadline = self.deadline - elapsed_seconds
        
        # 2. Urgency Check: Safety net to guarantee completion.
        # If remaining time is less than what's needed for a worst-case
        # (On-Demand) finish, we must use On-Demand now.
        min_time_to_finish_on_demand = work_remaining + self.restart_overhead
        if time_to_deadline <= min_time_to_finish_on_demand:
            return ClusterType.ON_DEMAND

        # 3. If the current region has spot, use it. It's the cheapest way to make progress.
        if has_spot:
            return ClusterType.SPOT

        # 4. Current region lacks spot. Find the best alternative region to switch to.
        # The best region is one with spot available now and the longest future streak.
        best_region_to_switch = -1
        max_streak = 0
        num_regions = self.env.get_num_regions()

        for r in range(num_regions):
            if self.get_spot_availability(r, current_time_step):
                # This region has spot now, calculate its continuous availability streak.
                streak = 0
                step = current_time_step
                while self.get_spot_availability(r, step):
                    streak += 1
                    step += 1
                
                if streak > max_streak:
                    max_streak = streak
                    best_region_to_switch = r

        if best_region_to_switch != -1:
            # A better region was found. Switch to it and use its Spot instance.
            current_region = self.env.get_current_region()
            if best_region_to_switch != current_region:
                self.env.switch_region(best_region_to_switch)
            return ClusterType.SPOT
            
        # 5. No spot available anywhere. Decide whether to wait or use On-Demand.
        # Calculate slack time: the buffer we have before a last-minute OD finish is required.
        slack = time_to_deadline - min_time_to_finish_on_demand
        
        if slack > self.env.gap_seconds:
            # We have enough slack to wait for one time step, hoping for spot to return.
            return ClusterType.NONE
        else:
            # Not enough slack to wait. Must use On-Demand to make progress.
            return ClusterType.ON_DEMAND