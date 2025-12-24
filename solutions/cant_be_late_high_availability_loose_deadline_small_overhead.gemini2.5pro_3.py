import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        """
        Optional initialization. Called once before evaluation.
        Read spec_path for configuration if needed.
        Must return self.
        """
        # --- Hyperparameters ---
        # Default values are set here, can be overridden by command-line arguments
        # parsed in _from_args.
        caution_buffer_hours = getattr(self.args, 'caution_buffer_hours', 4.0)
        finish_move_factor = getattr(self.args, 'finish_move_factor', 2.0)

        # --- Internal state setup ---
        # The panic buffer is set to one restart overhead. If slack is less
        # than this, a single preemption could cause a deadline miss.
        self.panic_buffer_sec_ = self.restart_overhead

        # The caution buffer separates the "Comfort" and "Caution" zones.
        self.caution_buffer_sec_ = caution_buffer_hours * 3600.0

        # The threshold for the "finishing move".
        self.finish_threshold_sec_ = finish_move_factor * self.restart_overhead

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Called at each time step. Return which cluster type to use next.

        Args:
            last_cluster_type: The cluster type used in the previous step
            has_spot: Whether spot instances are available this step

        Returns:
            ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        # Calculate current work progress.
        work_done = sum(end - start for start, end in self.task_done_time)
        work_remaining = self.task_duration - work_done

        # If the job is finished, do nothing to save cost.
        if work_remaining <= 0:
            return ClusterType.NONE

        # Finishing Move: If very close to completion, use On-Demand to be safe.
        if work_remaining < self.finish_threshold_sec_:
            return ClusterType.ON_DEMAND

        # Calculate time remaining and slack.
        current_time = self.env.elapsed_seconds
        time_to_deadline = self.deadline - current_time

        # Failsafe: if we can't finish even with on-demand, we have already lost.
        if work_remaining >= time_to_deadline:
            return ClusterType.ON_DEMAND

        slack = time_to_deadline - work_remaining

        # --- Zone-based Decision Logic ---

        # 1. Panic Zone: Critically low on slack. Must use On-Demand.
        if slack <= self.panic_buffer_sec_:
            return ClusterType.ON_DEMAND

        # 2. Caution Zone: Low on slack. Prioritize progress.
        if slack <= self.caution_buffer_sec_:
            return ClusterType.SPOT if has_spot else ClusterType.ON_DEMAND

        # 3. Comfort Zone (implicit: slack > caution_buffer_sec_):
        # Plenty of slack. Prioritize cost savings.
        return ClusterType.SPOT if has_spot else ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):  # REQUIRED: For evaluator instantiation
        """
        Adds strategy-specific arguments to the parser and instantiates the class.
        """
        parser.add_argument(
            '--caution-buffer-hours',
            type=float,
            default=4.0,
            help='The slack in hours below which the strategy becomes cautious.'
        )
        parser.add_argument(
            '--finish-move-factor',
            type=float,
            default=2.0,
            help=('Factor of restart_overhead. When work_remaining is below this, '
                  'switches to On-Demand.')
        )
        args, _ = parser.parse_known_args()
        return cls(args)
