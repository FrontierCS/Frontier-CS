from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "CantBeLateSolution"

    def solve(self, spec_path: str) -> "Solution":
        """
        Optional initialization.
        """
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decides the cluster type for the next time step.
        """
        # Retrieve environment state
        elapsed = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        total_duration = self.task_duration
        # Efficiently calculate total work done
        work_done = sum(self.task_done_time)
        deadline = self.deadline
        overhead = self.restart_overhead

        # Calculate remaining requirements
        work_remaining = total_duration - work_done
        time_remaining = deadline - elapsed

        # Calculate Slack: The amount of time we can afford to not make progress
        # Slack = Time Remaining - Work Remaining
        # If we ran perfectly efficiently from now on, we would finish with this much time left.
        slack = time_remaining - work_remaining

        # Define Safety Threshold
        # We switch to On-Demand (guaranteed) if slack drops below this buffer.
        # Factors for buffer size:
        # 1. Restart Overhead (~180s): We might incur this when switching to OD.
        # 2. Step Size (gap): We make decisions in discrete steps.
        # 3. Safety Margin: To prevent missing deadline due to simulation quirks or late preemptions.
        
        # A 1-hour (3600s) buffer is chosen because:
        # - It is small compared to the ~22h initial slack (low impact on optimal cost).
        # - It is large compared to overheads (high reliability against -100,000 penalty).
        
        safety_buffer = 3600.0  # 1 hour
        min_technical_buffer = (overhead * 3) + (gap * 2)
        threshold = max(safety_buffer, min_technical_buffer)

        # 1. Critical Condition: Low slack
        # If we are running out of time to handle interruptions, force On-Demand.
        if slack < threshold:
            return ClusterType.ON_DEMAND

        # 2. Economic Condition: High slack
        # If we have plenty of time, prefer Spot (cheaper).
        if has_spot:
            return ClusterType.SPOT

        # 3. Wait Condition: Spot unavailable, but high slack
        # Waiting costs $0. Using OD costs ~$3/hr. 
        # Since we have slack, we "spend" slack to save money by idling.
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)