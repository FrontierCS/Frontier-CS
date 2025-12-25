from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args):
        super().__init__(args)
        # Hyperparameters for the dynamic buffer strategy.
        # K-value determines the caution buffer size as a multiple of restart_overhead.
        # It scales linearly with job progress to become more conservative over time.
        self.K_start = 2.0  # K-value at 0% progress.
        self.K_end = 5.0    # K-value at 100% progress.
        # Panic buffer is a final safety net, as a multiple of the time step size.
        self.panic_buffer_margin = 1.0

    def solve(self, spec_path: str) -> "Solution":
        """
        Optional initialization. Called once before evaluation.
        Must return self.
        """
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Called at each time step. Return which cluster type to use next.
        """
        # 1. Calculate the current state of the job.
        work_done = sum(end - start for start, end in self.task_done_time)
        work_remaining = self.task_duration - work_done

        # If the job is finished, do nothing to save cost.
        if work_remaining <= 0:
            return ClusterType.NONE

        time_to_deadline = self.deadline - self.env.elapsed_seconds

        # If finishing is mathematically impossible, still use ON_DEMAND to minimize
        # the failure margin, as this might be better than giving up.
        if work_remaining > time_to_deadline:
            return ClusterType.ON_DEMAND

        # 2. Define dynamic thresholds for decision-making.
        
        # The panic buffer is the minimum slack tolerated before forcing ON_DEMAND.
        panic_buffer = self.panic_buffer_margin * self.env.gap_seconds

        # The caution buffer determines when to use ON_DEMAND over NONE if spot
        # is unavailable. It grows with job progress to increase conservatism.
        progress_fraction = work_done / self.task_duration if self.task_duration > 0 else 1.0
        k_multiplier = self.K_start + (self.K_end - self.K_start) * progress_fraction
        caution_buffer = k_multiplier * self.restart_overhead

        # 3. Apply the decision logic based on the current time buffer.
        current_buffer = time_to_deadline - work_remaining

        # PANIC MODE: If slack is critically low, force ON_DEMAND.
        if current_buffer <= panic_buffer:
            return ClusterType.ON_DEMAND

        # NORMAL/CAUTION MODE:
        if has_spot:
            # Always prefer cheap Spot instances when available.
            return ClusterType.SPOT
        else:
            # Spot is unavailable. Choose between expensive progress (ON_DEMAND)
            # or waiting (NONE).
            if current_buffer <= caution_buffer:
                # Buffer is shrinking; use ON_DEMAND to guarantee progress.
                return ClusterType.ON_DEMAND
            else:
                # Buffer is healthy; wait for Spot to become available again.
                return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        """Required method for evaluator instantiation."""
        args, _ = parser.parse_known_args()
        return cls(args)