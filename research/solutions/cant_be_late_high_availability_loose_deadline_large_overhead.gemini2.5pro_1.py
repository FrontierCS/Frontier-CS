from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args=None):
        super().__init__()
        self.safety_buffer_seconds = 0.0

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize strategy-specific parameters.
        This method is called once before the simulation starts.
        """
        # The safety buffer is a crucial hyperparameter. It determines how much
        # slack time we preserve to handle uncertainties like Spot preemptions
        # or long periods of Spot unavailability.
        # The buffer is defined as a multiple of the restart_overhead.
        # A factor of 17.5 was chosen based on the problem's 22-hour total slack
        # and 0.2-hour restart overhead, budgeting for a reasonable number of
        # potential preemptions during the 48-hour task.
        safety_buffer_factor = 17.5
        self.safety_buffer_seconds = safety_buffer_factor * self.restart_overhead
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Determine the cluster type to use for the next time step.
        This method implements a "Point of No Return" (PNR) strategy.
        """
        # 1. Calculate the remaining work.
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done

        # If the task is completed, no resources are needed.
        if work_remaining <= 1e-9:
            return ClusterType.NONE

        # 2. If Spot instances are available, always use them.
        # This is the most cost-effective way to make progress.
        if has_spot:
            return ClusterType.SPOT
        
        # 3. If Spot is unavailable, decide between On-Demand or waiting (NONE).
        # The decision is based on a "critical time". If the current time is
        # past this critical time, we must use On-Demand to avoid missing the
        # deadline. Otherwise, we can afford to wait for Spot.
        
        # The critical time is the latest moment we can start running work
        # exclusively on On-Demand and still finish by the deadline,
        # accounting for our safety buffer.
        critical_time = self.deadline - work_remaining - self.safety_buffer_seconds
        
        current_time = self.env.elapsed_seconds

        if current_time >= critical_time:
            # We are in the "critical zone". Our slack is below the safety
            # buffer. We must use On-Demand to guarantee progress.
            return ClusterType.ON_DEMAND
        else:
            # We have sufficient slack. We can wait for a cheaper Spot
            # instance to become available, saving costs.
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        """
        Instantiates the strategy from command-line arguments.
        This is required by the evaluator.
        """
        args, _ = parser.parse_known_args()
        return cls(args)