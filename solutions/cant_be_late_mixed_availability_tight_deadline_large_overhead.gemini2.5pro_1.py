import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "adaptive_proactive_scheduler"

    def __init__(self, args: argparse.Namespace = None):
        super().__init__()
        # This constructor is required to be compatible with the `_from_args`
        # method provided in the API specification.
        pass

    def solve(self, spec_path: str) -> "Solution":
        """
        Initializes the strategy's hyperparameters and state.
        This method is called once before the simulation begins.
        """
        # --- Hyperparameters ---
        self.patience_factor = 1.5
        self.panic_gap_multiplier = 1.5
        self.prior_total = 4
        self.prior_spot = 3
        
        # --- State Variables ---
        self.total_steps = 0
        self.spot_available_steps = 0
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        The core decision-making logic, called at each time step.
        """
        # 1. Check for task completion to avoid unnecessary costs.
        work_done = sum(self.task_done_time)
        remaining_work = self.task_duration - work_done
        if remaining_work <= 1e-9:
            return ClusterType.NONE

        # 2. Update the internal model of spot instance availability.
        self.total_steps += 1
        if has_spot:
            self.spot_available_steps += 1

        # 3. Calculate critical metrics for decision-making.
        current_time = self.env.elapsed_seconds
        time_to_deadline = self.deadline - current_time
        slack = time_to_deadline - remaining_work

        # 4. Define the "panic threshold". If slack falls below this level,
        # we must use on-demand instances to guarantee completion.
        panic_threshold = self.restart_overhead + (self.env.gap_seconds * self.panic_gap_multiplier)

        if slack <= panic_threshold:
            return ClusterType.ON_DEMAND

        # 5. If not in panic mode, use a spot instance if it's available.
        if has_spot:
            return ClusterType.SPOT

        # 6. Dilemma: Spot is not available, but not in panic mode.
        # Choose between waiting (NONE) or using on-demand (ON_DEMAND).

        # Estimate spot probability using observations and a stabilizing prior.
        effective_total = self.total_steps + self.prior_total
        effective_spot = self.spot_available_steps + self.prior_spot
        p_spot = effective_spot / effective_total
        p_spot = max(0.05, min(p_spot, 0.95))

        # Calculate the expected time to wait for a spot instance.
        expected_steps_to_wait = 1.0 / p_spot
        expected_time_to_wait = (expected_steps_to_wait - 1) * self.env.gap_seconds

        # The "wait threshold" is our decision boundary.
        wait_threshold = panic_threshold + (self.patience_factor * expected_time_to_wait)
        
        if slack > wait_threshold:
            return ClusterType.NONE
        else:
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser: argparse.ArgumentParser):
        """
        Required class method for evaluator instantiation.
        """
        args, _ = parser.parse_known_args()
        return cls(args)
