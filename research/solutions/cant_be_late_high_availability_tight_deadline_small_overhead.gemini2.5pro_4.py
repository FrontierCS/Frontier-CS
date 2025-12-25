import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        """
        Initializes the strategy with hyperparameters. This method is called once
        before the simulation starts.
        """
        # This hyperparameter controls the trade-off between cost and safety.
        # It defines the fraction of total available slack time (deadline - task_duration)
        # that should be reserved as a safety buffer.
        # A value of 0.5 means we aim to finish halfway through the slack period,
        # reserving the other half as a safety margin for unexpected spot unavailability
        # or preemptions near the deadline.
        self.SAFETY_BUFFER_FRACTION = 0.5

        # Internal flag to perform one-time initialization of strategy parameters
        # once the environment is available in the _step method.
        self._strategy_initialized = False
        return self

    def _initialize_strategy_parameters(self):
        """
        Calculates the strategy's operational parameters (e.g., target progress
        rate) once the environment details (like deadline) are known. This is
        called lazily on the first invocation of _step().
        """
        if self._strategy_initialized:
            return

        total_slack = self.deadline - self.task_duration
        
        # The safety buffer in seconds.
        final_buffer = total_slack * self.SAFETY_BUFFER_FRACTION
        
        # Our internal target deadline, which is earlier than the hard deadline.
        effective_deadline = self.deadline - final_buffer
        
        # This is the target rate of progress (work-seconds per wall-clock-second)
        # required to meet our effective_deadline.
        if effective_deadline > 0:
            self.target_rate = self.task_duration / effective_deadline
        else:
            # This edge case implies no slack and an impossible schedule.
            # Setting a very high target rate forces an aggressive strategy
            # (i.e., always using On-Demand).
            self.target_rate = float('inf')

        self._strategy_initialized = True

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        The main decision-making function, called at each time step.
        """
        if not self._strategy_initialized:
            self._initialize_strategy_parameters()

        work_done = sum(self.task_done_time)
        remaining_work = self.task_duration - work_done

        # If the task is already completed, do nothing to save cost.
        if remaining_work <= 0:
            return ClusterType.NONE

        current_time = self.env.elapsed_seconds
        time_to_deadline = self.deadline - current_time

        # --- Condition 1: Emergency Fallback ---
        # If the time left is less than the work needed, we have no slack.
        # We must use the guaranteed On-Demand resource to avoid failure.
        # A small buffer for the restart overhead is added as a safety margin.
        if time_to_deadline <= remaining_work + self.restart_overhead:
            return ClusterType.ON_DEMAND

        # --- Condition 2: Proportional Control Logic ---
        # Calculate the amount of work we should have completed by now to stay
        # on our target schedule.
        target_work_done = self.target_rate * current_time
        
        # Compare our actual progress to the target.
        is_behind_schedule = work_done < target_work_done

        if is_behind_schedule:
            # We've fallen behind our desired pace. Use On-Demand to catch up.
            return ClusterType.ON_DEMAND
        else:
            # We are on or ahead of our schedule. We can optimize for cost.
            if has_spot:
                # Cheap Spot instances are available, so we use them.
                return ClusterType.SPOT
            else:
                # No Spot available. Since we are ahead of schedule, we have a
                # time surplus that we can "spend" by waiting (doing nothing)
                # for Spot to become available again.
                return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser: argparse.ArgumentParser):
        """
        Required classmethod for the evaluator to instantiate the solution.
        """
        args, _ = parser.parse_known_args()
        return cls(args)