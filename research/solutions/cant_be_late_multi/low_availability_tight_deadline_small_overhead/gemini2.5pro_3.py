import json
from argparse import Namespace
import math
import csv

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """
    A multi-region scheduling strategy that uses pre-computation on spot availability
    traces to make informed, deterministic decisions.

    The strategy operates in two phases:
    1. Pre-computation (in `solve`):
       - It reads all provided spot availability trace files.
       - It identifies "safe" spot opportunities, defined as a time step where a spot
         instance is available and will not be preempted in the immediately following step.
       - It computes prefix sums and lookup tables for future safe spot availability
         to enable efficient decision-making at each step.

    2. Step-wise decision (in `_step`):
       At each time step, the strategy performs a two-level decision:
       a) Region Selection: It evaluates the potential of each region based on the
          number of safe spot slots available in a future window proportional to the
          remaining work. It switches to a better region if the gain in potential
          outweighs the time cost of the switch (restart overhead).
       b) Cluster Selection:
          - Panic Mode: If the remaining time to the deadline is critically low, it
            mandates using On-Demand instances to guarantee progress.
          - Spot Usage: If a "safe" spot instance is available in the current step,
            it's always chosen due to its low cost.
          - Wait or Work: If no safe spot is available, it calculates the waiting
            time for the next safe spot opportunity. If the current time slack allows
            for this wait without jeopardizing the deadline, it chooses to wait (NONE).
            Otherwise, it uses an On-Demand instance to make progress.
    """

    NAME = "my_strategy"  # REQUIRED: unique identifier

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the solution from spec_path config and pre-compute availability data.
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
        trace_files = config.get('trace_files', [])
        for trace_file in trace_files:
            try:
                with open(trace_file, 'r', newline='') as f:
                    content_sample = f.read(2048)
                    f.seek(0)
                    try:
                        dialect = csv.Sniffer().sniff(content_sample, delimiters=',')
                        reader = csv.reader(f, dialect)
                        header = next(reader)
                        if any(c.isalpha() for c in ''.join(header)):
                            pass
                        else:
                            f.seek(0)
                            reader = csv.reader(f, dialect)
                        trace = [bool(int(row[-1])) for row in reader]
                        self.spot_availability.append(trace)
                    except csv.Error:
                        f.seek(0)
                        self.spot_availability.append([bool(int(line.strip())) for line in f if line.strip()])
            except (IOError, ValueError):
                pass

        self.num_regions = len(self.spot_availability)
        self.num_steps = 0
        if self.num_regions > 0 and self.spot_availability[0]:
            self.num_steps = len(self.spot_availability[0])

        self.safe_spot_availability = []
        for r in range(self.num_regions):
            safe_trace = [False] * self.num_steps
            if self.num_steps > 0:
                for t in range(self.num_steps - 1):
                    if self.spot_availability[r][t] and self.spot_availability[r][t+1]:
                        safe_trace[t] = True
                if self.spot_availability[r][self.num_steps - 1]:
                    safe_trace[self.num_steps - 1] = True
            self.safe_spot_availability.append(safe_trace)

        self.safe_spot_prefix_sum = []
        for r in range(self.num_regions):
            prefix_sum = [0] * (self.num_steps + 1)
            for i in range(self.num_steps):
                prefix_sum[i+1] = prefix_sum[i] + self.safe_spot_availability[r][i]
            self.safe_spot_prefix_sum.append(prefix_sum)

        self.next_safe_spot = []
        for r in range(self.num_regions):
            next_s = [self.num_steps] * (self.num_steps + 1)
            last_safe_spot = self.num_steps
            for i in range(self.num_steps - 1, -1, -1):
                if self.safe_spot_availability[r][i]:
                    last_safe_spot = i
                next_s[i] = last_safe_spot
            self.next_safe_spot.append(next_s)

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state and pre-computed data.
        """
        remaining_work = self.task_duration - sum(self.task_done_time)
        if remaining_work <= 1e-9:
            return ClusterType.NONE

        current_step = int(self.env.elapsed_seconds / self.env.gap_seconds)
        if current_step >= self.num_steps or self.num_regions == 0:
            return ClusterType.ON_DEMAND

        # --- Region Selection ---
        remaining_work_steps = int(math.ceil(remaining_work / self.env.gap_seconds))
        horizon = min(remaining_work_steps, self.num_steps - current_step)
        
        potentials = []
        for r in range(self.num_regions):
            end_step = min(current_step + horizon, self.num_steps)
            avail_count = self.safe_spot_prefix_sum[r][end_step] - self.safe_spot_prefix_sum[r][current_step]
            potentials.append(avail_count)

        current_region = self.env.get_current_region()
        best_region_idx = max(range(self.num_regions), key=lambda i: potentials[i])
        
        switch_threshold = self.restart_overhead / self.env.gap_seconds
        if potentials[best_region_idx] > potentials[current_region] + switch_threshold:
            self.env.switch_region(best_region_idx)
            current_region = best_region_idx

        # --- Cluster Selection ---
        is_spot_safe_to_use = self.safe_spot_availability[current_region][current_step]

        remaining_time = self.deadline - self.env.elapsed_seconds
        required_time_for_od = remaining_work + self.remaining_restart_overhead
        risk_buffer = self.env.gap_seconds + self.restart_overhead

        # Panic mode: switch to OD if time is critically low.
        if remaining_time <= required_time_for_od + self.env.gap_seconds * 0.5:
            return ClusterType.ON_DEMAND

        # If a safe spot is available, it's the best option.
        if is_spot_safe_to_use:
            return ClusterType.SPOT
            
        # No safe spot now. Decide between waiting (NONE) or using OD.
        next_safe_spot_step = self.next_safe_spot[current_region][current_step]
        
        if next_safe_spot_step >= self.num_steps:
            return ClusterType.ON_DEMAND

        wait_steps = next_safe_spot_step - current_step
        wait_time = wait_steps * self.env.gap_seconds
        
        # Check if we can afford to wait.
        if remaining_time - wait_time > required_time_for_od + risk_buffer:
            return ClusterType.NONE
        else:
            return ClusterType.ON_DEMAND