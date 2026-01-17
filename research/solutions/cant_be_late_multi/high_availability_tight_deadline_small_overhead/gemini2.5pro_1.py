import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """
    A multi-region scheduling strategy that balances cost and deadline-awareness.

    The strategy operates in different modes based on the available "slack",
    which is the buffer time between the earliest possible completion time and the
    deadline.

    - GREEN Zone (High Slack): Prioritizes cost savings. It will prefer to wait
      (ClusterType.NONE) for a Spot instance to become available somewhere rather
      than using an On-Demand instance.

    - YELLOW Zone (Medium Slack): Balances cost and progress. If the current
      region lacks a Spot instance, it will switch to another region that has one.
      If no Spot instances are available anywhere, it uses On-Demand to avoid
      falling behind.

    - RED Zone (Low Slack): Prioritizes meeting the deadline. It avoids any risky
      or time-consuming actions like switching regions (which incurs an overhead).
      If Spot is not available, it immediately uses On-Demand to guarantee progress.

    To decide which region to switch to, the strategy calculates a "stability"
    score for each region, defined as the number of consecutive future time steps
    where a Spot instance is predicted to be available based on the provided traces.
    """
    NAME = "my_strategy"

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the solution from spec_path config.
        This method pre-loads and pre-processes the spot availability traces for
        all regions to enable fast lookups during the simulation.
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
        for trace_path in config['trace_files']:
            with open(trace_path) as f:
                trace_list = json.load(f)
                self.traces.append(bytearray(trace_list))

        self.num_regions = len(self.traces)
        
        self.stability_cache = {}
        
        self.lookahead_window = 48

        self.COMFORTABLE_SLACK = 8 * 3600
        self.CAUTIOUS_SLACK = 2 * 3600

        return self

    def _calculate_stability(self, region_idx: int, start_timestep: int) -> int:
        """
        Calculates the stability of a region, defined as the number of
        consecutive upcoming time steps with spot availability.
        Uses memoization to avoid re-computation.
        """
        cache_key = (region_idx, start_timestep)
        if cache_key in self.stability_cache:
            return self.stability_cache[cache_key]

        count = 0
        trace = self.traces[region_idx]
        trace_len = len(trace)
        
        limit = start_timestep + self.lookahead_window

        for i in range(start_timestep, trace_len):
            if i >= limit:
                break
            if trace[i] == 1:
                count += 1
            else:
                break
        
        self.stability_cache[cache_key] = count
        return count

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        This is the core logic of the strategy, called at each time step.
        """
        done_work = sum(self.task_done_time)
        remaining_work = self.task_duration - done_work

        if remaining_work <= 0:
            return ClusterType.NONE

        current_time = self.env.elapsed_seconds
        time_to_deadline = self.deadline - current_time
        
        effective_remaining_work = remaining_work + self.remaining_restart_overhead
        current_slack = time_to_deadline - effective_remaining_work

        if has_spot:
            return ClusterType.SPOT

        current_timestep = int(current_time / self.env.gap_seconds)
        
        best_alt_region = -1
        max_stability = -1
        
        for r in range(self.num_regions):
            if r == self.env.get_current_region():
                continue
            
            trace = self.traces[r]
            if current_timestep < len(trace) and trace[current_timestep] == 1:
                stability = self._calculate_stability(r, current_timestep)
                if stability > max_stability:
                    max_stability = stability
                    best_alt_region = r

        if current_slack <= self.CAUTIOUS_SLACK:
            return ClusterType.ON_DEMAND
        
        if best_alt_region != -1:
            self.env.switch_region(best_alt_region)
            return ClusterType.NONE
        else:
            if current_slack > self.COMFORTABLE_SLACK:
                return ClusterType.NONE
            else:
                return ClusterType.ON_DEMAND