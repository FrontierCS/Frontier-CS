import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "my_strategy"  # REQUIRED: unique identifier

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the solution from spec_path config and pre-compute helpers.
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

        # 1. Load spot availability traces from files
        self.spot_availability = []
        for trace_file in config["trace_files"]:
            try:
                with open(trace_file) as f:
                    trace = [bool(int(line)) for line in f if line.strip()]
                    self.spot_availability.append(trace)
            except (IOError, ValueError):
                # In case of file error, append an empty list
                self.spot_availability.append([])

        if not self.spot_availability or not self.spot_availability[0]:
            self.num_steps = 0
            return self

        num_regions = len(self.spot_availability)
        self.num_steps = len(self.spot_availability[0])

        # 2. Pre-compute future availability scores using a sliding window
        lookahead_window = 50  # Heuristic lookahead steps
        self.future_availability = [[0] * self.num_steps for _ in range(num_regions)]
        for r in range(num_regions):
            if self.num_steps == 0:
                continue

            current_sum = sum(self.spot_availability[r][0:min(lookahead_window, self.num_steps)])
            self.future_availability[r][0] = current_sum

            for t in range(1, self.num_steps):
                current_sum -= self.spot_availability[r][t - 1]
                if t + lookahead_window - 1 < self.num_steps:
                    current_sum += self.spot_availability[r][t + lookahead_window - 1]
                self.future_availability[r][t] = current_sum

        # 3. Pre-compute the next time step with any spot availability
        self.next_spot_step = [-1] * self.num_steps
        last_known_spot_step = -1
        for t in range(self.num_steps - 1, -1, -1):
            if any(self.spot_availability[r][t] for r in range(num_regions)):
                last_known_spot_step = t
            self.next_spot_step[t] = last_known_spot_step

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        work_done = sum(self.task_done_time)
        work_left = self.task_duration - work_done

        if work_left <= 0:
            return ClusterType.NONE

        time_left = self.deadline - self.env.elapsed_seconds
        current_time_step = int(self.env.elapsed_seconds / self.env.gap_seconds) if self.env.gap_seconds > 0 else 0

        if not hasattr(self, 'num_steps') or self.num_steps == 0 or current_time_step >= self.num_steps:
            # Fallback to On-Demand if trace data is unavailable or exhausted
            return ClusterType.ON_DEMAND

        # --- Panic Mode ---
        # Calculate time needed to finish if we switch to On-Demand now.
        overhead_if_switch_to_od = 0
        if last_cluster_type != ClusterType.ON_DEMAND:
            overhead_if_switch_to_od = self.restart_overhead

        time_needed_od = work_left + overhead_if_switch_to_od
        # Use one restart overhead as a safety margin
        safety_margin = self.restart_overhead

        if time_left <= time_needed_od + safety_margin:
            return ClusterType.ON_DEMAND

        # --- Normal Mode: Try to use Spot ---
        # 1. Spot is available in the current region
        if has_spot:
            return ClusterType.SPOT

        # 2. Spot not in current region, find the best region to switch to
        best_region_to_switch = -1
        max_future_score = -1

        num_regions = self.env.get_num_regions()
        for r in range(num_regions):
            if self.spot_availability[r][current_time_step]:
                future_score = self.future_availability[r][current_time_step]
                if future_score > max_future_score:
                    max_future_score = future_score
                    best_region_to_switch = r

        if best_region_to_switch != -1:
            self.env.switch_region(best_region_to_switch)
            return ClusterType.SPOT

        # 3. No Spot available anywhere now. Decide between On-Demand and None.
        slack = time_left - (time_needed_od + safety_margin)

        next_spot_avail_step = -1
        if current_time_step + 1 < self.num_steps:
            next_spot_avail_step = self.next_spot_step[current_time_step + 1]

        if next_spot_avail_step != -1:
            steps_to_wait = next_spot_avail_step - current_time_step
            time_to_wait = steps_to_wait * self.env.gap_seconds

            if slack > time_to_wait:
                return ClusterType.NONE

        # If no future spot is found, or we can't afford to wait, use On-Demand
        return ClusterType.ON_DEMAND