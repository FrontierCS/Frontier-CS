import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "adaptive_buffer_v1"

    def solve(self, spec_path: str) -> "Solution":
        """
        Optional initialization. Called once before evaluation.
        Read spec_path for configuration if needed.
        Must return self.
        """
        # --- Tunable Parameters ---
        # Base safety buffer in seconds. This is the minimum slack we want to maintain.
        # It provides a cushion for unexpected events like preemptions.
        # A value of 30 minutes (1800s) is chosen as a starting point.
        self.BASE_BUFFER = 1800.0

        # A multiplier for the longest observed spot unavailability period ("drought").
        # This makes the buffer adaptive. A higher factor means the strategy
        # becomes conservative more quickly in response to poor spot availability.
        self.DROUGHT_FACTOR = 1.2

        # --- State Variables ---
        # Tracks the duration of the current, ongoing spot unavailability period.
        self.current_drought_seconds = 0.0
        
        # Tracks the longest spot unavailability period seen so far.
        self.max_drought_seen_seconds = 0.0

        # Caching for total work done to avoid re-computation on every step.
        self._total_work_done_cache = 0.0
        self._task_done_time_len_cache = 0

        return self

    def _get_total_work_done(self) -> float:
        """
        Calculates and caches the total amount of work completed.
        This is a micro-optimization to avoid re-summing a potentially long list.
        """
        if len(self.task_done_time) == self._task_done_time_len_cache:
            return self._total_work_done_cache

        self._total_work_done_cache = sum(end - start for start, end in self.task_done_time)
        self._task_done_time_len_cache = len(self.task_done_time)
        return self._total_work_done_cache

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Called at each time step. Return which cluster type to use next.

        The core logic is to maintain a "slack" time, which is the amount of
        time we can afford to be idle before risking the deadline. This slack is
        compared against an adaptive safety buffer. If slack falls below the
        buffer, we switch to reliable On-Demand instances. Otherwise, we use
        Spot if available or wait if not. The buffer grows based on the longest
        observed period of Spot unavailability, making the strategy more
        conservative in low-availability environments.
        """
        # 1. Update state: Track spot unavailability "droughts".
        if has_spot:
            self.current_drought_seconds = 0.0
        else:
            self.current_drought_seconds += self.env.gap_seconds
        
        self.max_drought_seen_seconds = max(
            self.max_drought_seen_seconds, self.current_drought_seconds
        )

        # 2. Calculate current progress and available time slack.
        work_done = self._get_total_work_done()
        work_remaining = self.task_duration - work_done

        if work_remaining <= 1e-9:  # Floating point comparison for job completion.
            return ClusterType.NONE

        time_remaining_to_deadline = self.deadline - self.env.elapsed_seconds
        
        # Slack = Time left until deadline - Time needed to finish work.
        slack = time_remaining_to_deadline - work_remaining
        
        # 3. Calculate the adaptive safety buffer.
        adaptive_buffer = self.BASE_BUFFER + self.max_drought_seen_seconds * self.DROUGHT_FACTOR

        # 4. Make the decision based on the slack vs. buffer comparison.
        if slack < adaptive_buffer:
            # Not enough slack, must use the reliable option to guarantee progress.
            return ClusterType.ON_DEMAND
        else:
            # Plenty of slack, we can afford to use cheaper options or wait.
            if has_spot:
                # Use the cheapest option when available.
                return ClusterType.SPOT
            else:
                # Wait for Spot to become available to save costs.
                return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser: argparse.ArgumentParser):
        """
        Required classmethod for evaluator instantiation.
        """
        args, _ = parser.parse_known_args()
        return cls(args)
