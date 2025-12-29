import math
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    """
    This strategy employs a dynamic safety buffer to decide when to switch
    from cheap, unreliable Spot instances to expensive, reliable On-Demand instances.

    Core Logic:
    1.  At each step, calculate the `effective_work_remaining`, which is the actual
        task work plus any pending `restart_overhead` time from a previous preemption.
    2.  Calculate the `time_to_deadline`. The available "slack" is the difference
        between `time_to_deadline` and `effective_work_remaining`.
    3.  A `safety_buffer` is calculated, representing a minimum amount of slack
        we want to maintain. If the actual slack falls below this buffer,
        we switch to On-Demand to guarantee completion.
    4.  The `safety_buffer` is dynamic: it increases as the task progresses.
        This makes the strategy more risk-averse and cautious as it gets
        closer to the deadline, reducing the chance of failure due to a late-stage
        preemption.
    5.  If sufficient slack exists, the strategy prefers the cheapest option:
        - Use Spot instances if they are available.
        - If Spot is unavailable, wait (use NONE) to save costs, as the slack
          can absorb the delay.

    Preemption Detection:
    - Preemption is detected by observing a lack of progress in a timestep where a
      Spot instance was supposed to be running.
    - Upon detection, a `restarting_until` timestamp is set. This time is factored
      into the `effective_work_remaining` calculation.
    """
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        # State variables to track across timesteps
        self.last_work_done = 0.0
        self.restarting_until = 0.0

        # Hyperparameters for the dynamic safety buffer.
        # The buffer is K * restart_overhead, where K is interpolated
        # quadratically from K_MIN to K_MAX based on task progress.
        self.K_MIN = 1.5
        self.K_MAX = 4.0

        # Small tolerance for floating point comparisons
        self.EPSILON = 1e-6

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        current_time = self.env.elapsed_seconds
        gap_seconds = self.env.gap_seconds

        current_work_done = sum(end - start for start, end in self.task_done_time)

        # If the task is finished, do nothing to save cost.
        if current_work_done >= self.task_duration - self.EPSILON:
            return ClusterType.NONE

        # --- Preemption Detection ---
        progress_in_last_step = current_work_done - self.last_work_done
        if (last_cluster_type == ClusterType.SPOT and
            progress_in_last_step < gap_seconds * 0.5):
            # A preemption occurred. Set/reset the restart overhead period.
            self.restarting_until = current_time + self.restart_overhead

        self.last_work_done = current_work_done

        # --- Urgency Calculation ---
        work_remaining = self.task_duration - current_work_done
        time_to_deadline = self.deadline - current_time

        # Effective work remaining includes any ongoing restart overhead period.
        remaining_overhead_time = max(0, self.restarting_until - current_time)
        effective_work_remaining = work_remaining + remaining_overhead_time

        # --- Dynamic Safety Buffer Calculation ---
        progress_fraction = 0.0
        if self.task_duration > self.EPSILON:
            progress_fraction = current_work_done / self.task_duration
        
        # K increases quadratically, making the strategy more cautious near the end.
        k_value = self.K_MIN + (self.K_MAX - self.K_MIN) * (progress_fraction ** 2)
        safety_buffer = k_value * self.restart_overhead

        # --- Decision Logic ---
        if time_to_deadline <= effective_work_remaining + safety_buffer:
            # Slack is below our safety margin. Switch to reliable On-Demand.
            return ClusterType.ON_DEMAND
        else:
            # We have enough slack to risk using Spot or waiting.
            if has_spot:
                # Use cheap Spot instances.
                return ClusterType.SPOT
            else:
                # Spot is unavailable. Wait (do nothing) to save money.
                return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        """REQUIRED: For evaluator instantiation."""
        args, _ = parser.parse_known_args()
        return cls(args)