import json
from argparse import Namespace
import numpy as np

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """
    A multi-region scheduling strategy that uses full trace lookahead.
    """
    NAME = "lookahead_pro"

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

        # --- Pre-process trace files for lookahead ---
        raw_traces = []
        for trace_file in config["trace_files"]:
            try:
                with open(trace_file) as f:
                    trace = [int(line.strip()) > 0 for line in f.readlines()]
                    raw_traces.append(trace)
            except (IOError, ValueError):
                raw_traces.append([])
        
        if not raw_traces:
            max_len = 0
        else:
            max_len = max(len(t) for t in raw_traces) if raw_traces else 0

        padded_traces = []
        for t in raw_traces:
            padded_traces.append(t + [False] * (max_len - len(t)))

        if not padded_traces:
            self.spot_traces = np.empty((0, 0), dtype=bool)
        else:
            self.spot_traces = np.array(padded_traces, dtype=bool)

        num_regions, num_timesteps = self.spot_traces.shape
        
        if num_timesteps > 0:
            self.cumulative_spot = np.cumsum(self.spot_traces, axis=1, dtype=np.int32)
            self.next_spot_step = np.full((num_regions, num_timesteps), 
                                          fill_value=num_timesteps, dtype=np.int32)
            for r in range(num_regions):
                next_avail = num_timesteps
                for t in range(num_timesteps - 1, -1, -1):
                    if self.spot_traces[r, t]:
                        next_avail = t
                    self.next_spot_step[r, t] = next_avail
        else:
            self.cumulative_spot = np.empty((num_regions, 0), dtype=np.int32)
            self.next_spot_step = np.empty((num_regions, 0), dtype=np.int32)
        
        self.safety_margin = 2 * self.env.gap_seconds
        self.risk_factor = 1.5 

        return self

    def _get_future_availability(self, region_idx: int, start_step: int, end_step: int) -> int:
        """Calculates spot availability in a window using precomputed sums."""
        if self.cumulative_spot.shape[1] == 0:
            return 0
        
        max_step = self.cumulative_spot.shape[1] - 1
        start_step = min(start_step, max_step)
        end_step = min(end_step, max_step)
        
        if start_step < 0 or start_step > end_step:
            return 0

        end_sum = self.cumulative_spot[region_idx, end_step]
        start_sum = self.cumulative_spot[region_idx, start_step - 1] if start_step > 0 else 0
        return end_sum - start_sum

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state and full trace lookahead.
        """
        remaining_work = self.task_duration - sum(self.task_done_time)
        if remaining_work <= 0:
            return ClusterType.NONE

        current_seconds = self.env.elapsed_seconds
        time_to_deadline = self.deadline - current_seconds
        current_step = int(current_seconds // self.env.gap_seconds)
        num_regions, num_timesteps = self.spot_traces.shape

        on_demand_finish_time = remaining_work + self.restart_overhead
        if on_demand_finish_time >= time_to_deadline - self.safety_margin:
            return ClusterType.ON_DEMAND

        current_region = self.env.get_current_region()
        
        if has_spot:
            return ClusterType.SPOT

        slack = time_to_deadline - remaining_work
        
        can_afford_switch = slack > self.restart_overhead * self.risk_factor + self.safety_margin
        safe_current_step = min(current_step, num_timesteps - 1)

        if can_afford_switch and num_timesteps > 0:
            regions_with_spot_now = []
            for r in range(num_regions):
                if r != current_region and self.spot_traces[r, safe_current_step]:
                    regions_with_spot_now.append(r)

            if regions_with_spot_now:
                best_region_to_switch = -1
                max_future_avail = -1
                lookahead_steps = int(remaining_work / self.env.gap_seconds)
                
                for r in regions_with_spot_now:
                    future_avail = self._get_future_availability(r, safe_current_step, safe_current_step + lookahead_steps)
                    if future_avail > max_future_avail:
                        max_future_avail = future_avail
                        best_region_to_switch = r

                if best_region_to_switch != -1:
                    self.env.switch_region(best_region_to_switch)
                    return ClusterType.SPOT

        if num_timesteps == 0 or current_step >= num_timesteps:
            return ClusterType.ON_DEMAND

        next_avail_step = self.next_spot_step[current_region, safe_current_step]

        if next_avail_step >= num_timesteps:
            return ClusterType.ON_DEMAND

        steps_to_wait = next_avail_step - current_step
        time_to_wait = steps_to_wait * self.env.gap_seconds if steps_to_wait > 0 else 0

        projected_time_if_wait = time_to_wait + remaining_work + self.restart_overhead
        
        if projected_time_if_wait < time_to_deadline - self.safety_margin:
            return ClusterType.NONE
        else:
            return ClusterType.ON_DEMAND