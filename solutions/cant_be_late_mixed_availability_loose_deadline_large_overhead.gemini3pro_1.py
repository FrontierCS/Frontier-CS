from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "DeadlineAwareCostOptimizer"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Calculate work completed so far
        # self.task_done_time is a list of completed segment durations in seconds
        done_work = sum(self.task_done_time) if self.task_done_time else 0.0
        remaining_work = self.task_duration - done_work

        # If the task is finished (with small float tolerance), stop
        if remaining_work <= 1e-3:
            return ClusterType.NONE

        # Time management
        elapsed = self.env.elapsed_seconds
        remaining_time = self.deadline - elapsed

        # Calculate the absolute latest time we must start On-Demand to finish.
        # We model the time required as:
        # 1. The actual remaining work duration (OD runs at 1.0x speed)
        # 2. The restart overhead (incurred if we switch to OD from Spot/None)
        # 3. A safety buffer to account for discrete time steps and simulation variance
        
        # Base requirement: exact work time needed
        time_needed_for_od = remaining_work
        
        # If we are not currently running OD, we assume we'll pay the restart overhead to switch.
        # If we are already on OD, we don't pay it again to continue.
        if last_cluster_type != ClusterType.ON_DEMAND:
            time_needed_for_od += self.restart_overhead

        # Safety buffer definition:
        # - 3.0x the step gap: ensures we catch the threshold even if the step size is large
        # - Fixed constant of 900s (15 min): conservative padding given the large slack (22h) 
        #   and the severe penalty for missing the deadline.
        buffer = (3.0 * self.env.gap_seconds) + 900.0
        
        panic_threshold = time_needed_for_od + buffer

        # Strategy Logic:
        # 1. Panic Mode: If remaining time is close to the minimum required time, force On-Demand.
        #    This effectively guarantees the deadline is met by switching to the reliable resource
        #    before it's physically impossible to finish.
        if remaining_time <= panic_threshold:
            return ClusterType.ON_DEMAND

        # 2. Economy Mode: If we have plenty of slack (not in panic mode):
        #    a. If Spot is available, use it (cheapest option).
        if has_spot:
            return ClusterType.SPOT
        
        #    b. If Spot is unavailable, wait (NONE).
        #       We burn slack time but save money (cost=0 vs cost=OD).
        #       Since we checked panic_threshold, we know we have enough slack to afford waiting
        #       for Spot to potentially become available again.
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
