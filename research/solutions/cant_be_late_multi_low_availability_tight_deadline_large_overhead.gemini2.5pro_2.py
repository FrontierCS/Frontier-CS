import json
from argparse import Namespace
import csv
import bisect

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """
    A multi-region scheduling strategy that uses future spot trace information
    to make cost-effective decisions while ensuring the deadline is met.
    """

    NAME = "lookahead_scheduler"

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the solution from spec_path config and pre-load trace data.
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
        self.raw_spot_availability = []
        for trace_file in self.trace_files:
            region_avail = {}
            try:
                with open(trace_file, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    try:
                        first_row = next(reader)
                        if any(c.isalpha() for c in first_row[0]):
                             pass
                        else:
                            ts, avail = float(first_row[0]), bool(int(first_row[1]))
                            region_avail[ts] = avail
                    except (StopIteration, IndexError):
                        pass

                    for row in reader:
                        try:
                            ts, avail = float(row[0]), bool(int(row[1]))
                            region_avail[ts] = avail
                        except (ValueError, IndexError):
                            continue
            except FileNotFoundError:
                pass
            self.raw_spot_availability.append(region_avail)
        
        self.setup_done = False
        return self

    def _one_time_setup(self):
        """
        Performs one-time setup on the first call to _step.
        - Discretizes spot availability from timestamps to time steps.
        - Pre-computes a sorted list of spot window start times for each region
          to enable fast lookups.
        """
        num_regions = self.env.get_num_regions()
        gap = self.env.gap_seconds
        
        max_steps = int(self.deadline / gap) + 10 

        self.spot_avail_steps = []
        for r in range(num_regions):
            avail_steps = [False] * max_steps
            if r < len(self.raw_spot_availability):
                for ts, avail in self.raw_spot_availability[r].items():
                    step = int(round(ts / gap))
                    if step < max_steps:
                        avail_steps[step] = avail
            self.spot_avail_steps.append(avail_steps)

        self.spot_window_starts = []
        for r_avail in self.spot_avail_steps:
            starts = []
            is_down = True
            for i, is_up in enumerate(r_avail):
                if is_up and is_down:
                    starts.append(i)
                is_down = not is_up
            self.spot_window_starts.append(starts)

        self.setup_done = True

    def _find_next_spot_step(self, r: int, current_step: int) -> int or None:
        """Finds the next time step with spot availability using binary search."""
        starts = self.spot_window_starts[r]
        idx = bisect.bisect_left(starts, current_step)
        if idx < len(starts):
            return starts[idx]
        return None

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state and future spot availability.
        """
        if not self.setup_done:
            self._one_time_setup()

        remaining_work = self.task_duration - sum(self.task_done_time)
        if remaining_work <= 0:
            return ClusterType.NONE

        time_left = self.deadline - self.env.elapsed_seconds
        
        # 1. Panic Mode: If deadline is at risk, use On-Demand.
        time_needed_if_od_now = remaining_work
        if last_cluster_type == ClusterType.ON_DEMAND:
            time_needed_if_od_now += self.remaining_restart_overhead
        else:
            time_needed_if_od_now += self.restart_overhead

        if time_left <= time_needed_if_od_now:
            return ClusterType.ON_DEMAND

        # 2. Opportunistic Mode: Find the best spot opportunity.
        current_step = int(round(self.env.elapsed_seconds / self.env.gap_seconds))
        r_current = self.env.get_current_region()
        
        best_option = {'r': -1, 'cost': float('inf'), 'start_step': -1}

        for r in range(self.env.get_num_regions()):
            next_spot_step = self._find_next_spot_step(r, current_step)
            if next_spot_step is None:
                continue

            wait_steps = next_spot_step - current_step
            wait_time = wait_steps * self.env.gap_seconds

            overhead = self.restart_overhead
            is_continuing_spot = (
                r == r_current and
                last_cluster_type == ClusterType.SPOT and
                wait_steps == 0 and
                self.remaining_restart_overhead == 0
            )
            if is_continuing_spot:
                overhead = 0
            
            total_time_cost = wait_time + overhead

            if total_time_cost < best_option['cost']:
                best_option = {
                    'r': r,
                    'cost': total_time_cost,
                    'start_step': next_spot_step
                }
        
        min_spot_time_cost = best_option['cost']

        if min_spot_time_cost == float('inf'):
            return ClusterType.ON_DEMAND

        # 3. Decision: Check if the best spot plan is viable.
        if time_left > remaining_work + min_spot_time_cost:
            r_best = best_option['r']
            
            if r_best != r_current:
                self.env.switch_region(r_best)
                return ClusterType.NONE
            else:
                if current_step < best_option['start_step']:
                    return ClusterType.NONE
                else:
                    return ClusterType.SPOT
        else:
            return ClusterType.ON_DEMAND