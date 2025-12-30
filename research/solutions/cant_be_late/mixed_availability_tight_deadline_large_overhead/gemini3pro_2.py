from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "cant_be_late_solution"

    def solve(self, spec_path: str) -> "Solution":
        self.last_seen_type = ClusterType.NONE
        self.committed_work = 0.0
        self.current_segment_start = 0.0
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # 1. Update progress tracking
        # Detect if committed work increased (e.g., segment finished or interrupted)
        current_total_committed = sum(self.task_done_time)
        work_committed_update = (current_total_committed > self.committed_work)
        
        # Detect if cluster type switched since last step
        type_switched = (last_cluster_type != self.last_seen_type)
        
        if type_switched or work_committed_update:
            # Reset current segment tracker
            # If type switched, the change happened roughly at the start of this step/end of last
            self.current_segment_start = self.env.elapsed_seconds
            if type_switched:
                 self.current_segment_start -= self.env.gap_seconds
            
            self.last_seen_type = last_cluster_type
            self.committed_work = current_total_committed

        # Calculate pending progress in the current running segment
        pending_progress = 0.0
        if last_cluster_type != ClusterType.NONE:
            duration = self.env.elapsed_seconds - self.current_segment_start
            # Account for restart overhead (first X seconds is not progress)
            pending_progress = max(0.0, duration - self.restart_overhead)

        total_work_done = self.committed_work + pending_progress
        work_rem = max(0.0, self.task_duration - total_work_done)

        # 2. Determine Strategy
        # Safety buffer: 15 minutes (900s)
        buffer = 900 
        
        # Calculate Latest Start Time (LST) for On-Demand to guarantee completion
        # We act conservatively: assume we must pay overhead to start/restart OD.
        # This creates a stable behavior: once on OD (where we assume 0 overhead effectively 
        # for progress, but risk of restart requires overhead in calculation), we tend to stay.
        time_needed = work_rem + self.restart_overhead
        lst = self.deadline - time_needed - buffer

        # Critical Check: Are we past the point of no return?
        # If so, force On-Demand usage.
        if self.env.elapsed_seconds >= lst:
            return ClusterType.ON_DEMAND
        
        # If we have slack, prefer Spot instances to save cost
        if has_spot:
            return ClusterType.SPOT
            
        # If Spot is unavailable but we have plenty of slack, Wait (NONE).
        # This saves money compared to running OD unnecessarily.
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)