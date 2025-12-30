from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    """
    This strategy employs a dynamic safety buffer to decide when to switch
    from the cost-effective but risky Spot instances to the reliable but
    expensive On-Demand instances.

    The core concept is "slack", defined as the amount of time that can be
    wasted (e.g., by waiting for Spot or due to preemption overhead) while
    still being able to complete the task by the deadline using a guaranteed
    resource.
    Slack = (Time remaining until deadline) - (Work time remaining)

    The strategy compares this slack to a dynamically calculated safety buffer.
    If the slack falls below this buffer, it switches to On-Demand to guarantee
    timely completion. Otherwise, it prioritizes cost savings: using Spot
    instances when available, and pausing (NONE) when they are not, effectively
    "spending" slack to save money.

    The safety buffer is not static; it grows linearly with task completion.
    - It starts small, allowing for more aggressive, cost-saving decisions early
      in the job when there is ample time to recover from setbacks.
    - It increases as the job progresses, enforcing a more conservative stance
      to ensure the nearly-completed task is not jeopardized by late-stage
      disruptions.

    This adaptive approach aims to find a near-optimal balance between
    minimizing cost and strictly adhering to the hard deadline. The buffer
    parameters are tunable via command-line arguments for fine-tuning.
    """
    NAME = "my_solution"  # REQUIRED: unique identifier

    def solve(self, spec_path: str) -> "Solution":
        """
        Initializes the strategy's parameters and caching variables.
        """
        # Set buffer parameters from command-line arguments, with default values.
        # Default min_buffer is 1x restart_overhead (720s).
        # Default max_buffer is 10x restart_overhead (7200s, or 2 hours).
        self.min_buffer_seconds = getattr(self.args, 'min_buffer', 720.0)
        self.max_buffer_seconds = getattr(self.args, 'max_buffer', 7200.0)

        # Caching mechanism to efficiently calculate total work done.
        self._work_done_cache = 0.0
        self._task_done_segments_count = 0
        
        return self

    def _get_work_done(self) -> float:
        """
        Calculates total work done, caching results to avoid re-summing
        the entire `task_done_time` list at every step.
        """
        if len(self.task_done_time) > self._task_done_segments_count:
            new_segments = self.task_done_time[self._task_done_segments_count:]
            self._work_done_cache += sum(end - start for start, end in new_segments)
            self._task_done_segments_count = len(self.task_done_time)
        return self._work_done_cache

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        The main decision-making logic, executed at each time step.
        """
        # 1. Calculate current job progress.
        work_done = self._get_work_done()
        work_remaining = self.task_duration - work_done

        # If the task is finished, switch to NONE to stop incurring costs.
        if work_remaining <= 0:
            return ClusterType.NONE

        # 2. Calculate the dynamic safety buffer for the current step.
        if self.task_duration > 0:
            work_done_fraction = min(1.0, work_done / self.task_duration)
        else:
            work_done_fraction = 1.0
        
        current_safety_buffer = self.min_buffer_seconds + \
            (self.max_buffer_seconds - self.min_buffer_seconds) * work_done_fraction

        # 3. Calculate the current slack time.
        time_to_deadline = self.deadline - self.env.elapsed_seconds
        current_slack = time_to_deadline - work_remaining

        # 4. Make the decision based on comparing slack to the safety buffer.
        if current_slack <= current_safety_buffer:
            # Slack has fallen below the safety threshold.
            # Switch to On-Demand to guarantee completion.
            return ClusterType.ON_DEMAND
        else:
            # There is sufficient slack to take risks for cost savings.
            if has_spot:
                # Use the cheap Spot instance if it's available.
                return ClusterType.SPOT
            else:
                # Wait for Spot to become available again.
                return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):  # REQUIRED: For evaluator instantiation
        """
        Defines command-line arguments to allow tuning of the strategy.
        """
        parser.add_argument(
            '--min-buffer',
            type=float,
            default=720.0,
            help='Minimum safety buffer in seconds.'
        )
        parser.add_argument(
            '--max-buffer',
            type=float,
            default=7200.0,
            help='Maximum safety buffer in seconds.'
        )
        args, _ = parser.parse_known_args()
        return cls(args)