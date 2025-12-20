from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args=None):
        super().__init__()
        # This constructor accepts arguments from _from_args, as required by the API.
        # This solution uses hardcoded parameters, so `args` is unused.

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize strategy-specific state and parameters before the simulation starts.
        """
        # --- Tunable Parameters ---
        # Number of spot attempts to observe before trusting the adaptive buffer.
        self.warmup_steps = 100
        # A fixed buffer multiplier to use during the warmup phase for conservative estimation.
        self.warmup_buffer_multiplier = 3.0
        # A minimum safety buffer, as a multiplier of restart_overhead, to add to the
        # adaptive calculation. This ensures we are always robust to at least one failure.
        self.min_safety_buffer_multiplier = 1.0
        # The threshold of remaining slack (as a fraction of initial slack) below which
        # we stop waiting (NONE) for spot and start using ON_DEMAND to make progress.
        self.wait_for_spot_slack_threshold = 0.75

        # --- State for adaptive logic ---
        # Count of times a spot instance was attempted.
        self.spot_attempts = 0
        # Count of times a spot attempt resulted in no progress (a failure).
        self.preemptions = 0
        # Total work done at the previous timestep, used to calculate progress delta.
        self.last_work_done = 0.0
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Main decision logic, called at each time step of the simulation.
        """
        # 1. Update statistics based on the outcome of the last step
        current_work_done = sum(self.task_done_time)
        work_delta = current_work_done - self.last_work_done

        if last_cluster_type == ClusterType.SPOT:
            self.spot_attempts += 1
            # A spot attempt with negligible progress is considered a failure (e.g., preemption).
            if work_delta < 1e-6:
                self.preemptions += 1
        
        self.last_work_done = current_work_done

        # 2. Calculate current job state
        work_remaining = self.task_duration - current_work_done

        # If the job is finished, do nothing to minimize cost.
        if work_remaining <= 0:
            return ClusterType.NONE

        time_elapsed = self.env.elapsed_seconds
        time_to_deadline = self.deadline - time_elapsed
        
        # Calculate the time required to finish the rest of the job using only
        # reliable on-demand instances. This is our "point of no return" baseline.
        time_needed_for_od = work_remaining

        # 3. Determine the safety buffer
        # This buffer is the extra time we want to maintain, beyond the bare
        # minimum `time_needed_for_od`, before we switch to guaranteed ON_DEMAND.
        
        if self.spot_attempts < self.warmup_steps:
            # During the initial "warmup" period, use a fixed, conservative buffer
            # as we lack sufficient data to estimate the spot instance failure rate accurately.
            safety_buffer = self.warmup_buffer_multiplier * self.restart_overhead
        else:
            # After warmup, use an adaptive buffer based on the observed spot failure rate.
            # Laplace smoothing (add-one smoothing) avoids division by zero and extreme values.
            spot_failure_rate = (self.preemptions + 1.0) / (self.spot_attempts + 2.0)

            # Estimate the number of time steps needed to complete the remaining work.
            if self.env.gap_seconds > 1e-9:
                steps_remaining = work_remaining / self.env.gap_seconds
            else:
                steps_remaining = 0

            # Estimate the total time we are likely to lose to future spot failures
            # if we continue to use spot instances for the rest of the job.
            expected_time_loss = steps_remaining * spot_failure_rate * self.restart_overhead
            
            # The buffer is this expected loss, plus a fixed minimum for added safety.
            min_safety_buffer = self.min_safety_buffer_multiplier * self.restart_overhead
            safety_buffer = expected_time_loss + min_safety_buffer

        # 4. Make the primary decision: are we in the "danger zone"?
        # If time left is less than what we need for OD plus our buffer, we must switch
        # to the reliable On-Demand option to guarantee completion before the deadline.
        if time_to_deadline <= time_needed_for_od + safety_buffer:
            return ClusterType.ON_DEMAND
        
        # 5. If we have sufficient slack, decide between SPOT, ON_DEMAND, and NONE.
        if has_spot:
            # Spot is available and we have a comfortable time buffer, so use the cheapest option.
            return ClusterType.SPOT
        else:
            # Spot is not available. The choice is between waiting (NONE), which is free but
            # consumes our time slack, or making progress with ON_DEMAND, which costs more
            # but preserves our slack.
            
            current_slack = time_to_deadline - time_needed_for_od
            initial_slack = self.deadline - self.task_duration

            # If our initial slack was positive and we still have a large fraction of it,
            # we can afford to gamble and wait for spot to become available again.
            if initial_slack > 1e-9 and \
               (current_slack / initial_slack) > self.wait_for_spot_slack_threshold:
                 return ClusterType.NONE
            else:
                # If slack is diminishing, it's safer to use ON_DEMAND to guarantee
                # progress and avoid falling into the "danger zone" unexpectedly.
                return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        """Required method for evaluator instantiation."""
        args, _ = parser.parse_known_args()
        return cls(args)
