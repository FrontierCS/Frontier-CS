import json
from argparse import Namespace
import math

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """
    A multi-region scheduling strategy that leverages full knowledge of spot availability
    traces to make informed, heuristic-based decisions.

    The core idea is to balance cost-saving (using SPOT) with risk management
    (finishing before the deadline). The strategy is primarily driven by a "slack"
    calculation, which measures how much time can be afforded for non-productive
    actions like waiting or handling restart overheads.

    Strategy Overview:
    1. Pre-computation (`_initialize`): On the first step, the strategy loads all
       spot availability traces and pre-computes a lookup table for the number of
       future spot slots available from any point in time for each region. This
       allows for efficient, forward-looking decisions.

    2. Urgency Check: At each step, it calculates the critical time required to finish
       the remaining work. If the time left until the deadline is less than this
       critical time plus a safety buffer (equal to one restart overhead), it
       switches to the safe ON_DEMAND option to guarantee progress.

    3. Main Logic:
       - If SPOT is available in the current region, it's almost always the best choice:
         cheap and productive.
       - If SPOT is not available, the strategy evaluates three options:
         a) Switch Region: It checks if any other region has SPOT available *now*. If so,
            and if there's enough slack to absorb the region-switching overhead, it
            switches to the region with the most promising future spot availability.
         b) Wait (NONE): If no immediate switch is possible, it checks if a spot slot
            will become available in *any* region "soon" (defined as a duration less
            than a restart overhead). If so and there's enough slack, it waits.
         c) Use ON_DEMAND: If switching is too risky and waiting is too long, it
            falls back to using ON_DEMAND to ensure progress is made.

    This heuristic approach aims to mimic an optimal policy by aggressively pursuing
    cheap SPOT opportunities while constantly monitoring the risk of missing the
    deadline and switching to a guaranteed-progress mode when necessary.
    """

    NAME = "my_strategy"  # REQUIRED: unique identifier

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

        self.trace_files = config["trace_files"]
        self.initialized = False

        return self

    def _initialize(self):
        """
        One-time setup on the first call to _step, once self.env is available.
        """
        self.gap_seconds = self.env.gap_seconds
        self.num_regions = self.env.get_num_regions()

        self.spot_availability = []
        max_len = 0
        for trace_file in self.trace_files:
            try:
                with open(trace_file) as f:
                    trace = [bool(int(line.strip())) for line in f]
                    self.spot_availability.append(trace)
                    max_len = max(max_len, len(trace))
            except (FileNotFoundError, ValueError):
                # In case of missing or empty trace files, append an empty list.
                self.spot_availability.append([])

        if max_len == 0:
            max_len = int(self.deadline / self.gap_seconds) + 1

        for i in range(len(self.spot_availability)):
            pad_len = max_len - len(self.spot_availability[i])
            if pad_len > 0:
                self.spot_availability[i].extend([False] * pad_len)
        
        self.num_timesteps = max_len

        # Pre-compute future spot slot counts.
        # self.future_spot_slots[r][t] = total available slots in [t, end_time-1]
        self.future_spot_slots = [[0] * (self.num_timesteps + 1) for _ in range(self.num_regions)]
        for r in range(self.num_regions):
            for t in range(self.num_timesteps - 1, -1, -1):
                self.future_spot_slots[r][t] = self.future_spot_slots[r][t+1] + self.spot_availability[r][t]
        
        self.initialized = True

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        if not self.initialized:
            self._initialize()

        elapsed_seconds = self.env.elapsed_seconds
        work_done = sum(self.task_done_time)
        current_overhead = self.remaining_restart_overhead
        current_region = self.env.get_current_region()

        work_left = self.task_duration - work_done
        if work_left <= 1e-9:
            return ClusterType.NONE

        time_left = self.deadline - elapsed_seconds
        t_idx = int(elapsed_seconds / self.gap_seconds)
        if t_idx >= self.num_timesteps:
            t_idx = self.num_timesteps - 1

        # 1. Urgency Check: If time is tight, be safe.
        safety_buffer = self.restart_overhead
        if time_left <= work_left + current_overhead + safety_buffer:
            return ClusterType.ON_DEMAND

        # 2. Happy Path: Spot is available in the current region.
        if has_spot:
            return ClusterType.SPOT

        # 3. No spot locally. Decide whether to switch, wait, or use On-Demand.
        slack = time_left - (work_left + current_overhead)

        # Option A: Switch to another region with SPOT available now.
        if slack > self.restart_overhead:
            best_switch_region = -1
            max_future_spots = -1
            for r in range(self.num_regions):
                if r == current_region:
                    continue
                if t_idx < self.num_timesteps and self.spot_availability[r][t_idx]:
                    if self.future_spot_slots[r][t_idx] > max_future_spots:
                        max_future_spots = self.future_spot_slots[r][t_idx]
                        best_switch_region = r
            
            if best_switch_region != -1:
                self.env.switch_region(best_switch_region)
                return ClusterType.SPOT
        
        # Option B: Wait (NONE) for a spot to become available soon.
        horizon_steps = int(self.restart_overhead / self.gap_seconds) + 2
        min_wait_steps = float('inf')
        for dt in range(1, horizon_steps):
            next_t_idx = t_idx + dt
            if next_t_idx >= self.num_timesteps:
                break
            for r in range(self.num_regions):
                if self.spot_availability[r][next_t_idx]:
                    min_wait_steps = dt
                    break
            if min_wait_steps != float('inf'):
                break
        
        wait_time = min_wait_steps * self.gap_seconds
        if wait_time < self.restart_overhead and slack > wait_time:
            return ClusterType.NONE

        # Option C: Fallback to ON_DEMAND.
        return ClusterType.ON_DEMAND