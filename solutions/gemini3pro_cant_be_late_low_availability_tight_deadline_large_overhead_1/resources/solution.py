from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CantBeLate_Solution"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Retrieve environment state
        current_time = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        
        # Calculate remaining work
        # task_done_time is a list of completed segment durations
        work_done = sum(self.task_done_time)
        remaining_work = self.task_duration - work_done
        
        # If work is effectively done, return NONE
        if remaining_work <= 1e-6:
            return ClusterType.NONE

        # --- Panic Logic ---
        # Calculate the time required to finish if we switch to (or continue) On-Demand NOW.
        # If we are currently running On-Demand, we don't pay restart overhead.
        # If we are running Spot or are Paused (NONE), we must pay overhead to start OD.
        overhead_cost = 0.0
        if last_cluster_type != ClusterType.ON_DEMAND:
            overhead_cost = self.restart_overhead
            
        time_needed_to_finish = remaining_work + overhead_cost
        
        # The latest absolute time we must be running On-Demand to meet the deadline
        latest_possible_start = self.deadline - time_needed_to_finish
        
        # Safety Buffer:
        # We must act before crossing the latest_possible_start.
        # Since simulation proceeds in 'gap' steps, we need at least 'gap' buffer.
        # We add extra padding (max of 2 steps or 5 minutes) to be conservative against 
        # floating point issues or overhead variability.
        buffer = max(2.0 * gap, 300.0)
        
        # If we are within the buffer of the point-of-no-return, force On-Demand.
        if current_time >= (latest_possible_start - buffer):
            return ClusterType.ON_DEMAND

        # --- Cost Minimization Logic ---
        # We have sufficient slack to avoid On-Demand.
        
        if has_spot:
            # Spot is available and cheap. Use it.
            return ClusterType.SPOT
        else:
            # Spot is unavailable, but we have slack.
            # Waiting (NONE) costs 0. Running OD costs high.
            # Since OD availability is guaranteed later, waiting preserves the option
            # to use Spot if it returns, without risking the deadline (handled by panic logic).
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
