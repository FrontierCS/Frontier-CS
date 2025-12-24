from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CantBeLateSolution"

    def solve(self, spec_path: str) -> "Solution":
        # Initialize tracking variables
        self.last_elapsed = 0.0
        self.last_done_len = 0
        self.current_work_pending = 0.0
        self.overhead_remaining = 0.0
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Current time and step size
        now = self.env.elapsed_seconds
        dt = now - self.last_elapsed
        self.last_elapsed = now

        # Check for task completion updates (interruptions or finished segments)
        done_list = self.task_done_time
        done_len = len(done_list)
        
        interrupt_occurred = False
        if done_len > self.last_done_len:
            # A segment was committed to the list
            # Reset pending work accumulator as it is now in the list
            self.current_work_pending = 0.0
            self.last_done_len = done_len
            self.overhead_remaining = 0.0
            interrupt_occurred = True

        # Update pending progress
        # Only accumulate if we were running and didn't just have a list update
        if not interrupt_occurred and last_cluster_type in (ClusterType.SPOT, ClusterType.ON_DEMAND):
            # Calculate time spent on overhead vs actual work
            overhead_consumed = min(self.overhead_remaining, dt)
            self.overhead_remaining -= overhead_consumed
            
            work_done = dt - overhead_consumed
            self.current_work_pending += work_done

        # Calculate remaining work
        w_done_total = sum(done_list)
        w_rem = self.task_duration - w_done_total - self.current_work_pending
        
        if w_rem <= 1e-4:
            return ClusterType.NONE

        # Decision Logic
        # We define a safety buffer to ensure we can finish on On-Demand even if Spot fails.
        # Buffer includes overhead time and a safety margin (2 hours) for step granularity/unforeseen delays.
        overhead = self.restart_overhead
        buffer = 7200.0 # 2 hours safety margin
        
        # Time required to finish if we switch to OD immediately (including startup overhead)
        time_required_od = w_rem + overhead + buffer
        time_until_deadline = self.deadline - now
        
        # If we are close to the point of no return, force On-Demand
        if time_until_deadline < time_required_od:
            decision = ClusterType.ON_DEMAND
        elif has_spot:
            # If safe, prefer Spot
            decision = ClusterType.SPOT
        else:
            # If safe but no Spot, wait (save money)
            decision = ClusterType.NONE

        # Update overhead prediction for the next step
        if decision != ClusterType.NONE:
            # If we switch cluster type or if we were interrupted, we incur restart overhead
            if decision != last_cluster_type or interrupt_occurred:
                self.overhead_remaining = overhead
        else:
            # If we pause, any next start will be a switch/new launch, so overhead will apply then
            self.overhead_remaining = 0.0

        return decision

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
