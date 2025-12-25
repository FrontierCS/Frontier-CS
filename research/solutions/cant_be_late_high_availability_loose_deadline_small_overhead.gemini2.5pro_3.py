import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "expert_programmer_solution"

    def solve(self, spec_path: str) -> "Solution":
        """
        Initializes the strategy's state and parameters.
        """
        # State variable to track the end time of a restart overhead period.
        self.restarting_until = 0.0
        # State variable to track when we started waiting for an available spot instance.
        self.waiting_for_spot_since = -1.0

        # --- Tunable Parameters ---
        # Factor to determine the safety buffer. The strategy switches to
        # full on-demand when slack drops below this buffer.
        # buffer = factor * restart_overhead
        # A value of 20 corresponds to a 1-hour buffer (20 * 3 minutes).
        self.safety_buffer_factor = 20.0
        
        # Factor to determine the maximum time to wait for a spot instance
        # before using on-demand for a single step.
        # wait_time = factor * restart_overhead
        # A value of 10 corresponds to a 30-minute wait (10 * 3 minutes).
        self.max_wait_time_factor = 10.0
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Core decision-making logic called at each time step.
        """
        time_now = self.env.elapsed_seconds

        # 1. Detect preemption and manage restart overhead.
        # A preemption is detected if we requested SPOT in the last step but the
        # current cluster type is NONE (i.e., the instance was terminated).
        was_preempted = (last_cluster_type == ClusterType.SPOT and
                         self.env.cluster_type == ClusterType.NONE)
        if was_preempted:
            self.restarting_until = time_now + self.restart_overhead

        # If we are within a restart overhead period, no work can be done.
        # We choose NONE to avoid incurring costs for an idle instance.
        if time_now < self.restarting_until:
            return ClusterType.NONE

        # 2. Check if the task is complete.
        # If so, do nothing to minimize cost.
        if self.progress >= 1.0:
            return ClusterType.NONE

        # 3. Calculate key metrics for decision-making.
        work_remaining = self.task_duration * (1.0 - self.progress)
        time_until_deadline = self.deadline - time_now
        
        # Slack is the total time we can afford to be idle or restarting
        # and still finish on time using only on-demand instances.
        slack = time_until_deadline - work_remaining

        safety_buffer = self.safety_buffer_factor * self.restart_overhead

        # 4. Main decision logic based on available slack.

        # 4a. Safety Net: If slack is below the safety buffer, we are in a
        # critical phase. We must use ON_DEMAND to guarantee completion.
        if slack < safety_buffer:
            return ClusterType.ON_DEMAND

        # 4b. Ample Slack & Spot Available: This is the ideal case.
        # Use the cheap SPOT instance. Reset the wait timer.
        if has_spot:
            self.waiting_for_spot_since = -1.0
            return ClusterType.SPOT
        
        # 4c. Ample Slack & Spot Unavailable: We can afford to wait.
        else:
            # If we just found spot is unavailable, start the timer.
            if self.waiting_for_spot_since < 0:
                self.waiting_for_spot_since = time_now

            wait_duration = time_now - self.waiting_for_spot_since
            max_wait_time = self.max_wait_time_factor * self.restart_overhead

            if wait_duration < max_wait_time:
                # We haven't waited too long yet, so continue waiting (NONE).
                return ClusterType.NONE
            else:
                # We have waited long enough. Use ON_DEMAND for one step to make
                # some progress, then reset the timer to wait again.
                self.waiting_for_spot_since = -1.0
                return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        """Required method for evaluator instantiation."""
        # This strategy does not use command-line arguments, but the method
        # is required by the API.
        args, _ = parser.parse_known_args()
        return cls(args)