from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType
import math

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        """
        Optional initialization. Called once before evaluation.
        Read spec_path for configuration if needed.
        Must return self.
        """
        # Factor for the critical slack buffer, as a multiple of restart_overhead.
        # If slack is below this, we must use on-demand.
        self.critical_buffer_factor = 1.5

        # Factor for willingness to wait. Higher means more patient.
        # Comfortable slack threshold = T_critical + factor * expected_wait_time.
        self.wait_aggressiveness = 2.0

        # State for online estimation of spot availability (p).
        # Start with a Beta(2,2) prior, corresponding to 1 success and 1 failure.
        # This gives an initial p_estimate of 0.5 and avoids division by zero.
        self.spot_seen_count = 1
        self.total_steps = 2
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Called at each time step. Return which cluster type to use next.

        Args:
            last_cluster_type: The cluster type used in the previous step
            has_spot: Whether spot instances are available this step

        Returns:
            ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        # 1. Update online estimate of spot availability
        self.total_steps += 1
        if has_spot:
            self.spot_seen_count += 1
        p_estimate = self.spot_seen_count / self.total_steps

        # 2. Calculate current job state
        work_done = sum(end - start for start, end in self.task_done_time)
        work_remaining = self.task_duration - work_done

        if work_remaining <= 0:
            return ClusterType.NONE

        current_time = self.env.elapsed_seconds
        time_to_deadline = self.deadline - current_time
        
        # Slack: time buffer if we switch to on-demand for all remaining work.
        slack = time_to_deadline - work_remaining

        # 3. Define adaptive thresholds for decision-making
        t_critical = self.critical_buffer_factor * self.restart_overhead

        if p_estimate > 1e-9:
            expected_wait_time = self.env.gap_seconds / p_estimate
        else:
            expected_wait_time = float('inf')
        
        t_comfortable = t_critical + self.wait_aggressiveness * expected_wait_time

        # 4. Decision logic
        # If slack is critically low, we must use on-demand to guarantee progress.
        if slack <= t_critical:
            return ClusterType.ON_DEMAND

        # If spot is available and we're not in a critical state, always use it.
        if has_spot:
            return ClusterType.SPOT

        # Spot is unavailable. Decide whether to wait (NONE) or use on-demand.
        # If we have a comfortable amount of slack, we can afford to wait.
        if slack >= t_comfortable:
            return ClusterType.NONE
        else:
            # Otherwise, it's too risky to wait. Use on-demand to make progress.
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):  # REQUIRED: For evaluator instantiation
        args, _ = parser.parse_known_args()
        return cls(args)