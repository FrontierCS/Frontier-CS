from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    """
    This strategy uses an adaptive safety buffer to decide when to switch
    from cheap Spot instances to reliable On-Demand instances.

    The core idea is to calculate the available "slack" time: the amount of
    time that can be wasted before the deadline becomes unreachable even with
    On-Demand instances.

    If this slack falls below a dynamically calculated safety buffer, the
    strategy switches to On-Demand to guarantee completion. Otherwise, it
    greedily chooses Spot if available, or waits (NONE) if Spot is unavailable,
    to minimize costs.

    The safety buffer is a multiple of the restart_overhead. This multiplier
    decreases as the job progresses, making the strategy more conservative at
    the start (when there is more uncertainty and time for failures to accumulate)
    and more aggressive towards the end.
    """
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        """
        Initializes the strategy's parameters. Called once before evaluation.
        """
        # --- Tunable Parameters ---
        # These control the size of the safety buffer, which is a multiple (N)
        # of the restart_overhead. A larger N is more conservative (safer, but
        # potentially more expensive).

        # N when the job starts (0% progress). A value of 5 means the initial
        # buffer is 5 * 12 minutes = 1 hour, out of a 4-hour total slack.
        self.N_START = 5.0

        # N when the job is about to finish (100% progress). A smaller value
        # reflects less time for future risks. 1.5 * 12 = 18 minutes.
        self.N_END = 1.5

        # --- State Variables ---
        # We cache the total work required at the beginning to calculate
        # job progress reliably. It is initialized on the first call to _step.
        self._initial_task_duration = -1.0

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Called at each time step to decide which cluster type to use next.
        """
        # One-time initialization of the total task duration.
        if self._initial_task_duration < 0:
            self._initial_task_duration = self.task_duration
            # Handle edge case of a zero-duration task to avoid division by zero.
            if self._initial_task_duration <= 0:
                self._initial_task_duration = 1.0

        # 1. Calculate remaining work and job progress
        work_done = sum(self.task_done_time)
        work_rem = self._initial_task_duration - work_done

        # If the job is finished, do nothing to save costs.
        if work_rem <= 0:
            return ClusterType.NONE

        progress = min(1.0, work_done / self._initial_task_duration)

        # 2. Calculate the adaptive safety buffer
        # Linearly interpolate the buffer multiplier 'N' based on job progress.
        current_n_multiplier = self.N_START * (1.0 - progress) + self.N_END * progress
        safety_buffer = current_n_multiplier * self.restart_overhead

        # 3. Calculate current slack time
        time_rem_to_deadline = self.deadline - self.env.elapsed_seconds
        # Slack is the time left until the deadline minus the time absolutely
        # required to finish the remaining work using On-Demand.
        slack = time_rem_to_deadline - work_rem

        # 4. Make the scheduling decision
        if slack < safety_buffer:
            # Slack is below our safety margin. It's too risky to use Spot
            # or wait. We must make guaranteed progress with On-Demand.
            return ClusterType.ON_DEMAND
        else:
            # We have sufficient slack to be cost-effective.
            if has_spot:
                # Spot is available, use the cheapest option.
                return ClusterType.SPOT
            else:
                # Spot is not available. Wait for it, as we can afford the delay.
                return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        """
        Required classmethod for evaluator instantiation.
        """
        args, _ = parser.parse_known_args()
        return cls(args)