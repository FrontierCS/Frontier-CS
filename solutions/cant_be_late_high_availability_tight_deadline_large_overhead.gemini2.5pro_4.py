import argparse

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args: argparse.Namespace):
        super().__init__(args)
        # Tunable parameters for strategy optimization
        self.slack_threshold_factor: float = args.slack_threshold_factor
        self.safety_buffer_factor: float = args.safety_buffer_factor
        
        # This will be initialized in solve() once problem specs are available
        self.slack_threshold: float = 0.0

    def solve(self, spec_path: str) -> "Solution":
        """
        Optional initialization. Called once before evaluation.
        We calculate strategy parameters based on the problem specification.
        """
        # The "caution" threshold: if our time buffer drops below this value,
        # we start using On-Demand when Spot is unavailable.
        self.slack_threshold = self.slack_threshold_factor * self.restart_overhead
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Called at each time step. Returns which cluster type to use next.
        """
        # 1. Calculate current progress and remaining time/work
        time_now = self.env.elapsed_seconds
        time_to_deadline = self.deadline - time_now
        
        work_done = 0.0
        if self.task_done_time:
            # task_done_time is a list of (start, end) tuples for completed work
            work_done = sum(end - start for start, end in self.task_done_time)
            
        work_remaining = self.task_duration - work_done

        # 2. If the task is finished, do nothing to save cost.
        if work_remaining <= 1e-9:  # Use a small epsilon for float comparison
            return ClusterType.NONE

        # 3. Calculate the time needed for a guaranteed finish using On-Demand.
        # This includes a potential restart overhead if not already on an OD instance.
        od_finish_time = work_remaining
        if last_cluster_type != ClusterType.ON_DEMAND:
            od_finish_time += self.restart_overhead
        
        # 4. PANIC MODE: Absolute deadline check.
        # If remaining time is less than what's needed for a guaranteed OD finish,
        # we have no choice but to use OD to avoid the penalty.
        safety_buffer = self.safety_buffer_factor * self.env.gap_seconds
        if time_to_deadline <= od_finish_time + safety_buffer:
            return ClusterType.ON_DEMAND

        # 5. REGULAR MODE: We have some slack to play with.
        
        # Always prioritize cheap Spot instances if they are available.
        if has_spot:
            return ClusterType.SPOT
        
        # If Spot is unavailable, decide whether to wait (NONE) or pay for progress (ON_DEMAND).
        # This decision is based on our "effective slack": the time buffer before panic mode.
        effective_slack = time_to_deadline - od_finish_time
        
        if effective_slack <= self.slack_threshold:
            # Slack buffer is low. Use On-Demand to guarantee progress.
            return ClusterType.ON_DEMAND
        else:
            # We have enough slack. Wait for Spot to become available again to save costs.
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser: argparse.ArgumentParser) -> "Solution":
        """
        Adds strategy-specific arguments to the parser and instantiates the class.
        """
        parser.add_argument(
            "--slack_threshold_factor",
            type=float,
            default=8.0,
            help="Factor of restart_overhead to define the 'caution' slack threshold. "
                 "Below this threshold, ON_DEMAND is used if SPOT is unavailable."
        )
        parser.add_argument(
            "--safety_buffer_factor",
            type=float,
            default=2.0,
            help="Factor of gap_seconds for the 'panic' safety buffer before the deadline."
        )
        args, _ = parser.parse_known_args()
        return cls(args)
