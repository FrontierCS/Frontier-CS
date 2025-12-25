import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        """
        Optional initialization. Called once before evaluation.
        """
        # --- Hyperparameters ---
        
        # Multiplier for the panic threshold. If slack is less than this times
        # the restart overhead, we switch to ON_DEMAND unconditionally.
        self.PANIC_MULTIPLIER = 1.05

        # Base constant for the adaptive wait threshold. This value is scaled
        # by the estimated spot availability to decide when to wait for spot.
        self.BASE_WAIT_K = 1.5

        # Alpha for the Exponential Moving Average (EWMA) used to estimate
        # spot instance availability.
        self.EWMA_ALPHA = 0.001

        # Initial belief about spot availability before observing data.
        self.PRIOR_SPOT_AVAILABILITY = 0.5

        # --- State ---
        self.spot_availability_estimate = self.PRIOR_SPOT_AVAILABILITY
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Called at each time step. Return which cluster type to use next.
        """
        # 1. Update our estimate of spot availability using EWMA.
        current_spot_signal = 1.0 if has_spot else 0.0
        self.spot_availability_estimate = (
            (1 - self.EWMA_ALPHA) * self.spot_availability_estimate +
            self.EWMA_ALPHA * current_spot_signal
        )

        # 2. Calculate current job and time status.
        work_done = self.get_task_done_time()
        work_left = self.task_duration - work_done
        
        # If the job is finished, we don't need any resources.
        if work_left <= 0:
            return ClusterType.NONE

        time_now = self.env.elapsed_seconds
        time_to_deadline = self.deadline - time_now
        
        # Total time cost to finish the job on a reliable instance.
        on_demand_time_needed = work_left + self.env.remaining_restart_overhead
        
        # Slack is the extra time we have before the deadline, assuming
        # we run on on-demand instances from now until completion.
        slack = time_to_deadline - on_demand_time_needed

        # 3. Apply the decision-making strategy.

        # PANIC MODE: If slack is critically low, use ON_DEMAND to guarantee progress.
        panic_threshold = self.PANIC_MULTIPLIER * self.restart_overhead
        if slack <= panic_threshold:
            return ClusterType.ON_DEMAND

        # NORMAL MODE: We have enough slack to tolerate at least one preemption.
        if has_spot:
            # Spot is available and cheaper. Since we are not in panic mode, use it.
            return ClusterType.SPOT
        else:
            # Spot is not available. Decide between waiting (NONE) or making progress (ON_DEMAND).
            # The decision depends on an adaptive "wait threshold".
            epsilon = 1e-6
            wait_threshold = (
                (self.BASE_WAIT_K * self.restart_overhead) / 
                (self.spot_availability_estimate + epsilon)
            )
            
            wait_threshold = max(wait_threshold, panic_threshold)

            if slack > wait_threshold:
                # Slack is high enough to justify waiting for a spot instance.
                return ClusterType.NONE
            else:
                # Slack is getting low. Pay for on-demand to make guaranteed progress.
                return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        """
        Instantiates the strategy from command-line arguments.
        """
        args, _ = parser.parse_known_args()
        return cls(args)