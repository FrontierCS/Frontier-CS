import json
from argparse import Namespace
import sys

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "FutureSeeker"  # REQUIRED: unique identifier

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the solution from spec_path config and pre-process traces.
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

        self.traces = []
        try:
            for trace_file in config["trace_files"]:
                with open(trace_file) as f:
                    trace = [
                        bool(int(line.strip())) for line in f if line.strip()
                    ]
                    self.traces.append(trace)
        except (FileNotFoundError, IndexError, ValueError):
            self.traces = []

        if not self.traces:
            self.num_regions = 0
            return self

        self.num_regions = len(self.traces)
        self.num_timesteps = len(self.traces[0]) if self.traces else 0

        # Pre-calculate streaks of consecutive spot availability
        self.streaks = [
            [0] * self.num_timesteps for _ in range(self.num_regions)
        ]
        for r in range(self.num_regions):
            for t in range(self.num_timesteps - 1, -1, -1):
                if self.traces[r][t]:
                    if t == self.num_timesteps - 1:
                        self.streaks[r][t] = 1
                    else:
                        self.streaks[r][t] = 1 + self.streaks[r][t + 1]

        # Pre-calculate the next time step with spot availability
        self.next_spot = [
            [-1] * self.num_timesteps for _ in range(self.num_regions)
        ]
        for r in range(self.num_regions):
            next_s = -1
            for t in range(self.num_timesteps - 1, -1, -1):
                if self.traces[r][t]:
                    next_s = t
                if next_s != -1:
                    self.next_spot[r][t] = next_s

        return self

    def _step(
        self, last_cluster_type: ClusterType, has_spot: bool
    ) -> ClusterType:
        """
        Decide next action based on current state.
        """
        # Fallback logic if traces were not loaded
        if not hasattr(self, 'traces') or not self.traces:
            work_rem = self.task_duration - sum(self.task_done_time)
            time_left = self.deadline - self.env.elapsed_seconds
            if time_left <= work_rem + self.restart_overhead:
                 return ClusterType.ON_DEMAND
            if has_spot:
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND

        # 1. Calculate current state
        work_done = sum(self.task_done_time)
        work_rem = self.task_duration - work_done

        if work_rem <= 1e-6:
            return ClusterType.NONE

        time_elapsed = self.env.elapsed_seconds
        time_left = self.deadline - time_elapsed
        current_step = int(time_elapsed // self.env.gap_seconds)

        # Handle running past the end of the pre-computed trace data
        if current_step >= self.num_timesteps:
            if time_left <= work_rem:
                return ClusterType.ON_DEMAND
            return ClusterType.NONE

        # 2. Panic Mode: Switch to On-Demand if finishing on time is at risk
        time_needed_for_od = work_rem + self.restart_overhead
        if time_left <= time_needed_for_od:
            return ClusterType.ON_DEMAND

        current_region = self.env.get_current_region()

        # 3. Normal Mode
        # 3a. If spot is available in the current region, use it.
        if has_spot:
            return ClusterType.SPOT

        # 3b. No local spot. Look for the best region to switch to.
        best_region_to_switch = -1
        max_streak = 0
        for r in range(self.num_regions):
            if r == current_region:
                continue
            streak = self.streaks[r][current_step]
            if streak > max_streak:
                max_streak = streak
                best_region_to_switch = r

        if max_streak > 0:
            self.env.switch_region(best_region_to_switch)
            return ClusterType.SPOT

        # 3c. No spot available anywhere. Decide between local OD and waiting.
        slack = time_left - work_rem
        next_spot_step = self.next_spot[current_region][current_step]

        if next_spot_step != -1:
            wait_seconds = (
                next_spot_step - current_step
            ) * self.env.gap_seconds
            if slack > wait_seconds + self.restart_overhead:
                return ClusterType.NONE

        return ClusterType.ON_DEMAND
