import argparse

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        self.total_work_done = 0.0
        self.last_work_done_len = 0

        # This value represents the "pressure" at which we switch
        # from waiting (NONE) to using ON_DEMAND when spot is not available.
        # Pressure = work_remaining / time_to_deadline
        # Initial pressure = 48h/70h ~= 0.686. A pressure of 1.0 means no slack.
        # A higher value is more aggressive (waits longer, saves money).
        # A lower value is more conservative (uses OD earlier, costs more).
        self.PRESSURE_THRESHOLD = 0.92
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # 1. Update progress efficiently
        if len(self.task_done_time) > self.last_work_done_len:
            new_work = sum(self.task_done_time[self.last_work_done_len:])
            self.total_work_done += new_work
            self.last_work_done_len = len(self.task_done_time)

        # 2. Calculate current state
        work_remaining = self.task_duration - self.total_work_done

        if work_remaining <= 1e-9:
            return ClusterType.NONE

        time_to_deadline = self.deadline - self.env.elapsed_seconds

        # 3. Decision Logic - ordered by criticality

        # Condition Red: Point of no return for On-Demand.
        # If time left is less than or equal to work left, we must use the
        # guaranteed On-Demand instance or we will fail.
        if time_to_deadline <= work_remaining:
            return ClusterType.ON_DEMAND

        # Condition Orange: Point of no return for Spot.
        # If there isn't enough time to absorb a `restart_overhead` from a
        # preemption, we cannot risk using Spot. Must use On-Demand.
        if has_spot and time_to_deadline <= work_remaining + self.restart_overhead:
            return ClusterType.ON_DEMAND

        # Best case: Spot is available and it's safe to use it.
        if has_spot:
            return ClusterType.SPOT

        # No spot case: Decide whether to use costly On-Demand or wait (NONE).
        
        # Failsafe for division by zero.
        if time_to_deadline <= 1e-9:
            return ClusterType.ON_DEMAND
            
        pressure = work_remaining / time_to_deadline
        
        if pressure > self.PRESSURE_THRESHOLD:
            # Pressure is too high; our slack is too low for the work left.
            # We must make progress using On-Demand.
            return ClusterType.ON_DEMAND
        else:
            # Pressure is manageable. We can afford to wait for Spot to return.
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser: argparse.ArgumentParser):
        args, _ = parser.parse_known_args()
        return cls(args)
