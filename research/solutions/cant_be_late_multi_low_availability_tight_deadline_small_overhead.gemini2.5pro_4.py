import json
from argparse import Namespace
import math

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """A multi-region scheduling strategy using trace-based lookahead."""

    NAME = "lookahead_scheduler"

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

        self.spot_traces = []
        for trace_file in config["trace_files"]:
            try:
                with open(trace_file) as tf:
                    trace = [int(line.strip()) for line in tf if line.strip()]
                    self.spot_traces.append(trace)
            except (IOError, ValueError):
                self.spot_traces.append([])

        self.spot_availability_cumsum = []
        for trace in self.spot_traces:
            cumsum = [0] * (len(trace) + 1)
            for i in range(len(trace)):
                cumsum[i + 1] = cumsum[i] + trace[i]
            self.spot_availability_cumsum.append(cumsum)

        self.LOOKAHEAD_FACTOR = 5.0
        self.SWITCH_GAIN_THRESHOLD = 1.0

        return self

    def _get_spot_in_window(self, region_idx: int, start_step: int, end_step: int) -> int:
        """Helper to get spot availability score using cumulative sums."""
        if region_idx >= len(self.spot_availability_cumsum):
            return 0

        cumsum = self.spot_availability_cumsum[region_idx]
        max_len = len(cumsum) - 1

        start_step = min(start_step, max_len)
        end_step = min(end_step, max_len)

        if start_step >= end_step:
            return 0

        return cumsum[end_step] - cumsum[start_step]

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        work_done = sum(self.task_done_time)
        work_left = self.task_duration - work_done

        if work_left <= 0:
            return ClusterType.NONE

        time_left = self.deadline - self.env.elapsed_seconds

        if time_left < work_left:
            return ClusterType.ON_DEMAND

        current_step = int(self.env.elapsed_seconds // self.env.gap_seconds)
        current_region = self.env.get_current_region()

        # Point of No Return (PNR) check
        overhead_if_choose_od = self.restart_overhead if last_cluster_type != ClusterType.ON_DEMAND else 0.0
        time_needed_for_od = work_left + overhead_if_choose_od
        if time_needed_for_od >= time_left:
            return ClusterType.ON_DEMAND

        # Prefer Spot if available
        if has_spot:
            return ClusterType.SPOT

        # Spot not available. Decide to switch, wait, or use ON_DEMAND.
        num_regions = self.env.get_num_regions()
        
        # Evaluate switching regions
        lookahead_duration = self.LOOKAHEAD_FACTOR * self.restart_overhead
        lookahead_steps = max(1, int(lookahead_duration / self.env.gap_seconds))

        start = current_step + 1
        end = start + lookahead_steps

        region_scores = [self._get_spot_in_window(r, start, end) for r in range(num_regions)]

        best_region_idx = region_scores.index(max(region_scores))
        max_score = region_scores[best_region_idx]
        current_region_score = region_scores[current_region]

        overhead_in_steps = self.restart_overhead / self.env.gap_seconds
        
        # Safety check: enough slack for switch overhead + one future potential overhead
        can_afford_switch = time_left > work_left + 2 * self.restart_overhead

        if best_region_idx != current_region and \
           max_score > current_region_score + overhead_in_steps + self.SWITCH_GAIN_THRESHOLD and \
           can_afford_switch:

            self.env.switch_region(best_region_idx)

            new_region_has_spot = False
            if best_region_idx < len(self.spot_traces) and current_step < len(self.spot_traces[best_region_idx]):
                 new_region_has_spot = self.spot_traces[best_region_idx][current_step] == 1

            if new_region_has_spot:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND

        # Not switching. Decide between ON_DEMAND and NONE.
        slack = time_left - work_left
        can_afford_to_wait = slack > self.env.gap_seconds + self.restart_overhead

        spot_is_coming_soon = False
        if current_region < len(self.spot_traces) and current_step + 1 < len(self.spot_traces[current_region]):
            if self.spot_traces[current_region][current_step + 1] == 1:
                spot_is_coming_soon = True

        if spot_is_coming_soon and can_afford_to_wait:
            return ClusterType.NONE
        else:
            return ClusterType.ON_DEMAND
