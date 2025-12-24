from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    """
    This strategy minimizes cost by aggressively using Spot instances while
    dynamically managing the risk of missing the deadline. It calculates a
    "point of no return" based on an adaptive model of Spot instance stability.

    Core Logic:
    1.  **Adaptive Overhead Estimation**: The strategy learns the "cost" of using
        Spot instances by observing how frequently they are preempted. It tracks
        total Spot usage time and the number of preemptions to estimate an
        average uptime. This is used to calculate an `overhead_factor`, which
        predicts how much extra compute time will be needed for restarts. This
        estimate is continuously updated using an exponential moving average.

    2.  **Dynamic "Must-Work" Threshold**: When Spot is unavailable, the decision
        to use expensive On-Demand or wait (NONE) is critical. The strategy
        calculates the total expected compute time needed to finish the job,
        factoring in the learned overhead. It compares this to the actual
        wall-clock time remaining until the deadline.
        
        The switch to On-Demand is triggered if:
           `time_remaining <= (work_remaining * (1 + overhead_factor)) + safety_buffer`

    3.  **Decision Policy**:
        - If Spot is available: Always use it.
        - If Spot is unavailable:
            - If the "must-work" threshold is crossed: Use ON_DEMAND.
            - Otherwise: Use NONE and wait for Spot to return.
    """
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        # State for adaptive learning of spot instance behavior
        self.num_preemptions = 0
        self.total_spot_time = 0.0
        self.was_on_spot = False

        # Model Parameters
        # Initial guess for the overhead factor, assuming a pessimistic average
        # spot uptime of 2x the restart overhead (e.g., 6 minutes).
        # overhead_factor = restart_overhead / average_spot_uptime
        self.overhead_factor = 0.5
        
        # A fixed 1-hour safety buffer to protect against model inaccuracies
        # or unusually long periods of spot unavailability.
        self.safety_buffer_seconds = 3600.0
        
        # Learning rate for the exponential moving average that updates the
        # overhead_factor, balancing stability and responsiveness.
        self.learning_rate = 0.1

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # 1. Update statistics based on the outcome of the previous step
        if last_cluster_type == ClusterType.SPOT:
            self.total_spot_time += self.env.gap_seconds
            self.was_on_spot = True
        elif last_cluster_type == ClusterType.ON_DEMAND:
            self.was_on_spot = False
        
        # A preemption event is approximated by a transition from a spot-active
        # state to spot becoming unavailable.
        if self.was_on_spot and not has_spot:
            self.num_preemptions += 1
            self.was_on_spot = False

            # Update the learned overhead factor if we have enough data
            if self.total_spot_time > 1.0:
                avg_uptime = self.total_spot_time / self.num_preemptions
                if avg_uptime > 1.0:
                    observed_factor = self.restart_overhead / avg_uptime
                    # Use an exponential moving average to smoothly update the estimate
                    self.overhead_factor = (
                        (1 - self.learning_rate) * self.overhead_factor +
                        self.learning_rate * observed_factor
                    )

        # 2. Make the decision for the current step
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done

        if work_remaining <= 0:
            return ClusterType.NONE

        if has_spot:
            # Always use the cheaper Spot instance when it is available
            return ClusterType.SPOT

        # If Spot is not available, decide between On-Demand and waiting
        time_remaining = self.deadline - self.env.elapsed_seconds

        # Estimate the total compute time needed, including future restart overheads
        estimated_future_compute_time = work_remaining * (1 + self.overhead_factor)
        
        # Define the critical threshold for when we must work to avoid failure
        must_work_threshold = estimated_future_compute_time + self.safety_buffer_seconds

        if time_remaining <= must_work_threshold:
            # Time slack has run out; use On-Demand to guarantee progress
            return ClusterType.ON_DEMAND
        else:
            # Sufficient slack exists; wait for Spot to become available again
            return ClusterType.NONE
            
    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
