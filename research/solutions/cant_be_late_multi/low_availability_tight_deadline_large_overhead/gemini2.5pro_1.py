import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """
    A multi-region scheduling strategy that uses pre-computed trace data
    to make informed, proactive decisions. It balances cost-saving on spot
    instances with the need to meet a hard deadline by employing a
    "panic mode" to switch to reliable on-demand instances when necessary.
    """

    NAME = "lookahead_optimizer"

    def solve(self, spec_path: str) -> "Solution":
        """
        Initializes the strategy and pre-computes lookahead data from traces.
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

        # --- Pre-computation Stage ---

        # 1. Load spot availability traces from files
        self.spot_traces = []
        for trace_file in config["trace_files"]:
            with open(trace_file) as f:
                trace = [line.strip() == '1' for line in f if line.strip()]
                self.spot_traces.append(trace)

        if not self.spot_traces:
            self.max_steps = 0
            self.streaks_cache = []
            self.next_spot_cache = []
            return self

        self.max_steps = len(self.spot_traces[0])
        num_regions = len(self.spot_traces)

        # 2. Pre-compute future consecutive spot streaks for each step
        # This allows for O(1) lookup of a region's quality at any time step.
        self.streaks_cache = [[0] * self.max_steps for _ in range(num_regions)]
        for r in range(num_regions):
            trace = self.spot_traces[r]
            current_streak = 0
            for i in range(self.max_steps - 1, -1, -1):
                if trace[i]:
                    current_streak += 1
                else:
                    current_streak = 0
                self.streaks_cache[r][i] = current_streak

        # 3. Pre-compute the next available spot step for each step
        # This helps decide efficiently whether to wait (NONE) or use On-Demand.
        self.next_spot_cache = [[-1] * self.max_steps for _ in range(num_regions)]
        for r in range(num_regions):
            trace = self.spot_traces[r]
            next_available_step = -1
            for i in range(self.max_steps - 1, -1, -1):
                self.next_spot_cache[r][i] = next_available_step
                if trace[i]:
                    next_available_step = i

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decides the next action at each time step based on pre-computed data.
        """
        # 1. State Calculation
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done

        if work_remaining <= 0:
            return ClusterType.NONE

        time_to_deadline = self.deadline - self.env.elapsed_seconds
        
        current_step = int(self.env.elapsed_seconds // self.env.gap_seconds)
        if current_step >= self.max_steps:
            # Beyond known trace data, act conservatively
            current_step = self.max_steps - 1
        
        # 2. Panic Mode: Switch to On-Demand if deadline is critical
        # This is a conservative check assuming a restart is needed to switch to OD.
        required_time = work_remaining + self.restart_overhead
        if time_to_deadline <= required_time:
            return ClusterType.ON_DEMAND

        # 3. Region Selection Logic
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()

        # Find the best region based on pre-computed future spot streaks
        best_streak = 0
        best_region_idx = -1
        for r in range(num_regions):
            streak = self.streaks_cache[r][current_step]
            if streak > best_streak:
                best_streak = streak
                best_region_idx = r
        
        current_streak = self.streaks_cache[current_region][current_step]

        # Decide whether to switch region. We switch if the current region has no
        # spot available now, a better one exists, and we can afford the time
        # cost of the switch.
        if best_region_idx != -1 and best_region_idx != current_region and current_streak == 0:
            slack = time_to_deadline - work_remaining
            if slack > self.restart_overhead + self.env.gap_seconds:
                self.env.switch_region(best_region_idx)
                # After switching to a region with a good spot streak, use SPOT
                return ClusterType.SPOT

        # 4. Action in Current Region (if no switch was made)
        if has_spot:
            return ClusterType.SPOT
        else:
            # No spot available here. Decide between waiting (NONE) or using OD.
            slack = time_to_deadline - work_remaining
            
            # Find when spot is next available in this region using the cache
            next_spot_step = self.next_spot_cache[current_region][current_step]
            
            if next_spot_step != -1:
                # Time we would lose by waiting for the next spot window
                time_to_wait = (next_spot_step - current_step) * self.env.gap_seconds
                # If we have more slack than the time we need to wait, pause.
                if slack > time_to_wait:
                    return ClusterType.NONE
            
            # If no future spot or not enough slack to wait, use ON_DEMAND.
            return ClusterType.ON_DEMAND