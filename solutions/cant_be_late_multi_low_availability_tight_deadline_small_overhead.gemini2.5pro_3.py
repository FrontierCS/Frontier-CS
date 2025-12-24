import json
from argparse import Namespace
import math

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """
    A multi-region scheduling strategy that aims to minimize cost by maximizing
    spot instance usage, while ensuring the task finishes before the deadline.

    The strategy is based on these principles:
    1.  Deadline-Awareness: The primary goal is to finish the task. A "panic mode"
        is triggered if the remaining time is just enough to finish the task using
        reliable on-demand instances. In this mode, only on-demand is used.
    2.  Informed Decisions: The strategy pre-processes historical spot availability
        traces to make predictions about future availability. This information is
        used for both region switching and deciding whether to wait for a spot
        instance.
    3.  Cost-Effectiveness:
        - Spot instances are heavily preferred over on-demand due to their lower cost.
        - The strategy will opt to wait (incurring no cost) for a spot instance
          to become available if it calculates that there is enough slack time
          before the deadline.
        - Region switching is performed conservatively, only when the current
          region lacks spot availability and a better region is available, and
          the time cost of switching (restart overhead) can be afforded.
    4.  Efficiency: All computationally intensive calculations on the traces, such as
        finding the next available spot or calculating availability density, are
        pre-computed during initialization to ensure the per-step decision logic
        is extremely fast, meeting the performance requirements of the evaluation
        environment.
    """

    NAME = "deadline_aware_spot_maximizer"

    def solve(self, spec_path: str) -> "Solution":
        """
        Initializes the solution from a spec file, loading configuration and
        pre-processing spot availability traces for efficient lookups.
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

        self._load_traces(config.get("trace_files", []))
        self._precompute_trace_data()

        return self

    def _load_traces(self, trace_files: list[str]):
        """Loads spot availability traces from files."""
        self.traces = []
        for trace_file in trace_files:
            with open(trace_file) as f:
                trace = [line.strip() == '1' for line in f if line.strip()]
                self.traces.append(trace)

        self.max_trace_len = 0
        if self.traces:
            self.max_trace_len = max(len(t) for t in self.traces) if self.traces else 0

    def _precompute_trace_data(self):
        """Performs pre-computation on traces for O(1) lookups during stepping."""
        num_regions = len(self.traces)
        if num_regions == 0:
            return

        # Precompute prefix sums for fast window-based availability scoring
        self.prefix_sum_traces = [[0] * (len(self.traces[r]) + 1) for r in range(num_regions)]
        for r in range(num_regions):
            for i in range(len(self.traces[r])):
                self.prefix_sum_traces[r][i+1] = self.prefix_sum_traces[r][i] + self.traces[r][i]

        # Precompute the index of the next available spot for each time step
        self.next_spot_step = [[math.inf] * len(self.traces[r]) for r in range(num_regions)]
        for r in range(num_regions):
            last_seen_spot = math.inf
            for i in range(len(self.traces[r]) - 1, -1, -1):
                if self.traces[r][i]:
                    last_seen_spot = i
                self.next_spot_step[r][i] = last_seen_spot
    
    def _is_spot_available(self, region_idx: int, timestep_idx: int) -> bool:
        """Checks predicted spot availability for a given region and timestep."""
        if 0 <= region_idx < len(self.traces) and 0 <= timestep_idx < len(self.traces[region_idx]):
            return self.traces[region_idx][timestep_idx]
        return False

    def _get_region_score(self, region_idx: int, start_idx: int, end_idx: int) -> int:
        """Calculates spot availability score for a region over a time window using prefix sums."""
        if not hasattr(self, 'prefix_sum_traces') or not (0 <= region_idx < len(self.prefix_sum_traces)):
            return 0
        
        prefix_sums = self.prefix_sum_traces[region_idx]
        trace_len = len(prefix_sums) - 1

        safe_start = min(start_idx, trace_len)
        safe_end = min(end_idx, trace_len)
        
        if safe_start >= safe_end:
            return 0
            
        return prefix_sums[safe_end] - prefix_sums[safe_start]

    def _find_best_region(self, current_timestep_idx: int, time_to_deadline: float) -> int:
        """Finds the region with the highest predicted future spot availability."""
        if not hasattr(self, 'traces') or not self.traces or self.env.get_num_regions() <= 1:
            return self.env.get_current_region()

        # Dynamic lookahead window based on time remaining
        window_size = int(time_to_deadline / self.env.gap_seconds) if self.env.gap_seconds > 0 else 0
        
        start_idx = current_timestep_idx
        end_idx = start_idx + window_size
        
        current_region = self.env.get_current_region()
        best_region = current_region
        best_score = self._get_region_score(current_region, start_idx, end_idx)

        for r in range(self.env.get_num_regions()):
            if r == current_region:
                continue
            
            score = self._get_region_score(r, start_idx, end_idx)
            if score > best_score:
                best_score = score
                best_region = r
        
        return best_region

    def _find_next_spot_wait_steps(self, region_idx: int, current_timestep_idx: int) -> int:
        """Finds the number of steps to wait for the next spot in a region."""
        if not hasattr(self, 'next_spot_step') or not (0 <= region_idx < len(self.next_spot_step)) or not (0 <= current_timestep_idx < len(self.next_spot_step[region_idx])):
             return math.inf

        next_spot_idx = self.next_spot_step[region_idx][current_timestep_idx]
        if math.isinf(next_spot_idx):
            return math.inf
        
        # If the precomputed next spot is the current step, we need the one after.
        if next_spot_idx <= current_timestep_idx:
            start_search_idx = current_timestep_idx + 1
            if start_search_idx < len(self.next_spot_step[region_idx]):
                next_spot_idx = self.next_spot_step[region_idx][start_search_idx]
            else:
                return math.inf
        
        if not math.isinf(next_spot_idx):
            return next_spot_idx - current_timestep_idx
        
        return math.inf


    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """Decides the next action (region and cluster type) for the current timestep."""
        
        remaining_work = self.task_duration - sum(self.task_done_time)
        if remaining_work <= 0:
            return ClusterType.NONE

        time_to_deadline = self.deadline - self.env.elapsed_seconds
        current_timestep_idx = int(self.env.elapsed_seconds / self.env.gap_seconds) if self.env.gap_seconds > 0 else 0
        current_region = self.env.get_current_region()
        
        # --- Panic Mode ---
        # If the time required to finish with on-demand exceeds the time to deadline,
        # we must use on-demand without fail.
        required_on_demand_time = remaining_work + self.remaining_restart_overhead
        if required_on_demand_time >= time_to_deadline:
            return ClusterType.ON_DEMAND

        # --- Region Switching Logic ---
        # Consider switching only if the current region has no spot available.
        if not has_spot:
            best_future_region = self._find_best_region(current_timestep_idx, time_to_deadline)
            if best_future_region != current_region and self._is_spot_available(best_future_region, current_timestep_idx):
                # Can we afford the restart overhead for switching?
                if remaining_work + self.restart_overhead < time_to_deadline:
                    self.env.switch_region(best_future_region)
                    return ClusterType.SPOT

        # --- Cluster Type Selection ---
        if has_spot:
            # If not in panic mode and spot is available, always use it.
            return ClusterType.SPOT
        else:
            # No spot, and we decided not to switch. Choose between ON_DEMAND and NONE.
            slack_time = time_to_deadline - required_on_demand_time
            
            # Calculate how long we'd have to wait for a spot in the current region.
            steps_to_wait = self._find_next_spot_wait_steps(current_region, current_timestep_idx)
            time_to_wait = steps_to_wait * self.env.gap_seconds
            
            # If we have enough slack to wait for the next spot, do so.
            if slack_time > time_to_wait:
                return ClusterType.NONE
            else:
                # Not enough slack to wait, must make progress with on-demand.
                return ClusterType.ON_DEMAND
