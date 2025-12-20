import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    """
    An adaptive strategy that balances cost-saving on SPOT instances with the risk
    of missing the deadline. It continuously estimates SPOT availability and
    preemption rates to calculate a "point of no return" time. If the current
    time is past this point, it switches to reliable ON_DEMAND instances to
    guarantee completion. Otherwise, it aggressively uses SPOT when available
    or waits if not.
    """
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        """
        Initializes the strategy's state and hyperparameters.
        """
        # --- Hyperparameters ---
        # Initial guess for SPOT availability (fraction of time available).
        self.INITIAL_AVAILABILITY = 0.75
        # Initial guess for preemption rate (per SPOT time step).
        self.INITIAL_PREEMPTION_RATE = 0.01
        # Smoothing factor for Exponential Moving Average (EMA) of availability.
        self.AVAILABILITY_ALPHA = 0.005
        # Smoothing factor for EMA of preemption rate.
        self.PREEMPTION_ALPHA = 0.01
        # Minimum assumed availability to prevent division by zero and over-pessimism.
        self.AVAILABILITY_FLOOR = 0.05
        # A safety buffer for the risk of preemption in the immediate next step.
        # Expressed as a factor of restart_overhead.
        self.IMMEDIATE_RISK_BUFFER_FACTOR = 1.0

        # --- State Variables ---
        self.ema_availability = self.INITIAL_AVAILABILITY
        self.ema_preemption_rate = self.INITIAL_PREEMPTION_RATE
        self.last_task_done_len = 0
        self.work_done_so_far = 0.0
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decision-making logic for each time step.
        """
        # 1. Update progress state
        current_len = len(self.task_done_time)
        if current_len > self.last_task_done_len:
            # Aggregate newly completed work segments.
            self.work_done_so_far += sum(self.task_done_time[self.last_task_done_len:])
        
        work_remaining = self.task_duration - self.work_done_so_far

        # If the task is complete, do nothing.
        if work_remaining <= 1e-9:
            return ClusterType.NONE

        # 2. Update risk estimators (preemption and availability) based on last step's outcome
        # a) Preemption Rate Estimation
        if last_cluster_type == ClusterType.SPOT:
            work_was_done = (current_len > self.last_task_done_len)
            is_preempted = 1.0 if not work_was_done else 0.0
            self.ema_preemption_rate = (self.PREEMPTION_ALPHA * is_preempted + 
                                       (1 - self.PREEMPTION_ALPHA) * self.ema_preemption_rate)
        
        # b) Availability Estimation
        has_spot_int = 1.0 if has_spot else 0.0
        self.ema_availability = (self.AVAILABILITY_ALPHA * has_spot_int +
                                 (1 - self.AVAILABILITY_ALPHA) * self.ema_availability)
        
        # Update state for the next step
        self.last_task_done_len = current_len

        # 3. Calculate the "point of no return"
        time_to_deadline = self.deadline - self.env.elapsed_seconds

        # Use the estimated availability, with a floor to remain robust.
        effective_availability = max(self.ema_availability, self.AVAILABILITY_FLOOR)
        
        # Estimate the total wall-clock time required to finish on SPOT, accounting for
        # expected periods of unavailability.
        expected_spot_runtime = work_remaining / effective_availability
        
        # From the expected runtime, estimate the number of future SPOT steps.
        # Add epsilon to prevent division by zero.
        num_expected_spot_steps = expected_spot_runtime / (self.env.gap_seconds + 1e-9)

        # Estimate the total time that will be lost to restart overheads from future preemptions.
        expected_preemption_overhead = (num_expected_spot_steps *
                                        self.ema_preemption_rate *
                                        self.restart_overhead)
                                        
        # Add a fixed buffer for the immediate risk of being preempted in the next step.
        immediate_risk_buffer = self.IMMEDIATE_RISK_BUFFER_FACTOR * self.restart_overhead

        # This is the total time we must have left to safely continue with the SPOT strategy.
        critical_time_needed = (expected_spot_runtime + 
                                expected_preemption_overhead + 
                                immediate_risk_buffer)

        # 4. Make the final decision
        if time_to_deadline <= critical_time_needed:
            # We are past the point of no return. The risk of using SPOT is too high.
            # We must switch to the reliable ON_DEMAND to guarantee finishing on time.
            return ClusterType.ON_DEMAND
        else:
            # We have sufficient slack. We can afford to pursue the cheaper SPOT option.
            if has_spot:
                # Use SPOT if it's available.
                return ClusterType.SPOT
            else:
                # Wait for SPOT to become available again.
                return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser: argparse.ArgumentParser):
        """
        Instantiates the strategy from command-line arguments.
        """
        # This implementation does not use command-line arguments for hyperparameters,
        # but this method is required by the evaluator.
        args, _ = parser.parse_known_args()
        return cls(args)
