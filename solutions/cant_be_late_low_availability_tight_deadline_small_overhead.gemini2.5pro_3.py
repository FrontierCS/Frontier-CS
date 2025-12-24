import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "pressure_and_slack_strategy"

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the strategy with tuned parameters.
        """
        # Threshold for schedule pressure. If (work_left / time_left) > threshold, use OD.
        # Initial pressure for the given problem is 48/52 ~= 0.923.
        self.pressure_threshold = 0.98

        # Threshold for absolute slack. If (time_left - work_left) < threshold, use OD.
        # Set as a multiple of restart_overhead to handle preemptions/unavailability.
        slack_overhead_multiplier = 20
        # self.restart_overhead is initialized in the base Strategy class.
        self.slack_threshold_s = slack_overhead_multiplier * self.restart_overhead

        # Caching variables for performance.
        self._work_done_cache = 0.0
        self._task_done_len_cache = 0

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Main decision-making logic, called at each time step.
        """
        # --- 1. Calculate current job progress ---
        if len(self.task_done_time) > self._task_done_len_cache:
            new_segments = self.task_done_time[self._task_done_len_cache:]
            self._work_done_cache += sum(end - start for start, end in new_segments)
            self._task_done_len_cache = len(self.task_done_time)
        
        work_left = self.task_duration - self._work_done_cache

        if work_left <= 1e-9:
            return ClusterType.NONE

        # --- 2. Calculate time and risk metrics ---
        time_to_deadline = self.deadline - self.env.elapsed_seconds
        
        if time_to_deadline <= 0:
            return ClusterType.ON_DEMAND

        time_needed_for_od = work_left + self.env.remaining_overhead

        # --- 3. Make a decision based on the strategy ---

        # PANIC MODE: If there's not enough time left even with full on-demand,
        # we must use on-demand.
        if time_needed_for_od >= time_to_deadline:
            return ClusterType.ON_DEMAND

        # GREEDY SPOT: If spot is available and we're not in panic mode, always take it.
        # The cost savings are high, and the risk is managed by the thresholds below.
        if has_spot:
            return ClusterType.SPOT

        # NO SPOT: Decide between ON_DEMAND (safe, expensive) and NONE (risky, free).
        
        # Metric 1: Absolute slack buffer
        slack_seconds = time_to_deadline - time_needed_for_od
        is_slack_low = slack_seconds < self.slack_threshold_s

        # Metric 2: Schedule pressure
        pressure = time_needed_for_od / time_to_deadline
        is_pressure_high = pressure > self.pressure_threshold

        if is_slack_low or is_pressure_high:
            # Safety buffer is eroding. Use On-Demand for guaranteed progress.
            return ClusterType.ON_DEMAND
        else:
            # We have a comfortable buffer. Wait for a cheap Spot instance.
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser: argparse.ArgumentParser) -> "Solution":
        """
        Required classmethod for evaluator instantiation.
        """
        args, _ = parser.parse_known_args()
        return cls(args)
