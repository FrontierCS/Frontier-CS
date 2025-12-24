import argparse
from collections import deque
from typing import Deque, Optional, List, Tuple

# Assuming these are provided by the evaluation environment's packages
# In a real scenario, these would be `from sky_spot.strategies.strategy import Strategy`
# and `from sky_spot.utils import ClusterType`. For standalone execution, we define placeholders.
try:
    from sky_spot.strategies.strategy import Strategy
    from sky_spot.utils import ClusterType
except ImportError:
    # --- Placeholder classes for standalone testing ---
    class ClusterType:
        SPOT = "SPOT"
        ON_DEMAND = "ON_DEMAND"
        NONE = "NONE"

    class Env:
        def __init__(self):
            self.elapsed_seconds = 0.0
            self.gap_seconds = 60.0
            self.cluster_type = ClusterType.NONE

    class Strategy:
        def __init__(self, args):
            self.env = Env()
            self.task_duration: float = 48 * 3600
            self.task_done_time: List[Tuple[float, float]] = []
            self.deadline: float = 52 * 3600
            self.restart_overhead: float = 0.05 * 3600

        def solve(self, spec_path: str) -> "Strategy":
            raise NotImplementedError

        def _step(self, last_cluster_type: str, has_spot: bool) -> str:
            raise NotImplementedError

        @classmethod
        def _from_args(cls, parser: argparse.ArgumentParser):
            raise NotImplementedError
    # --- End of placeholder classes ---


class Solution(Strategy):
    """
    This strategy uses a dynamic safety buffer based on recent spot availability
    to decide when to switch from cost-effective Spot instances to reliable
    On-Demand instances. The core idea is to calculate the 'slack' time: the
    difference between the time remaining until the deadline and the time
    required to finish the remaining work on an On-Demand instance.
    If this slack falls below a dynamically calculated `safety_buffer`, the
    strategy switches to On-Demand to guarantee progress. Otherwise, it
    aggressively uses Spot instances when available to minimize cost, or waits
    (NONE) if Spot is unavailable, conserving money while it has sufficient slack.
    The `safety_buffer` adapts to observed spot availability over a rolling
    window. If spot availability has been high, the buffer is small, allowing for
    more risk-taking. If availability has been low, the buffer increases, making
    the strategy more conservative.
    """
    NAME = "adaptive_buffer_strategy"

    def solve(self, spec_path: str) -> "Solution":
        # --- Hyperparameters ---
        # Duration for the sliding window to calculate recent spot availability.
        self.WINDOW_DURATION_S: float = 2 * 3600  # 2 hours

        # Min/max safety buffer bounds, interpolated based on availability.
        # MIN_BUFFER: Used when spot availability is 100%. A non-zero floor
        # accounts for unexpected long outages. Set to 10x restart overhead.
        self.MIN_BUFFER_S: float = 10 * (0.05 * 3600)  # 30 minutes

        # MAX_BUFFER: Used when spot availability is 0%. Capped at a portion of
        # the initial slack to ensure some attempt at using Spot is always made.
        self.MAX_BUFFER_S: float = 2.5 * 3600  # 2.5 hours

        # DEFAULT_BUFFER: Used at the beginning before enough data is collected.
        self.DEFAULT_BUFFER_S: float = 1.5 * 3600  # 1.5 hours

        # --- State Variables ---
        self.spot_availability_history: Optional[Deque[int]] = None
        self.history_sum: float = 0.0
        self.window_size_steps: Optional[int] = None

        return self

    def _get_work_done(self) -> float:
        """Calculates the total work completed so far."""
        if not self.task_done_time:
            return 0.0
        return sum(end - start for start, end in self.task_done_time)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decision logic for each time step.
        """
        # 1. Initialization on the first call to determine window size in steps.
        if self.spot_availability_history is None:
            if self.env.gap_seconds > 0:
                self.window_size_steps = int(self.WINDOW_DURATION_S / self.env.gap_seconds)
                # Ensure window size is at least 1 for the deque.
                self.window_size_steps = max(1, self.window_size_steps)
            else:
                # Safeguard for an unlikely gap_seconds of 0.
                self.window_size_steps = 1
            self.spot_availability_history = deque(maxlen=self.window_size_steps)

        # 2. Update state with current spot availability using an O(1) running sum.
        current_spot_status = 1 if has_spot else 0
        if len(self.spot_availability_history) == self.window_size_steps:
            self.history_sum -= self.spot_availability_history[0]
        self.spot_availability_history.append(current_spot_status)
        self.history_sum += current_spot_status

        # 3. Calculate the adaptive safety buffer.
        # Wait until we have a minimum amount of data to avoid noisy estimates.
        min_history_len = max(1, self.window_size_steps / 10)
        if len(self.spot_availability_history) < min_history_len:
            safety_buffer = self.DEFAULT_BUFFER_S
        else:
            avg_availability = self.history_sum / len(self.spot_availability_history)
            # Linearly interpolate buffer based on unavailability (1 - avg_availability)
            unavailability_factor = 1.0 - avg_availability
            safety_buffer = self.MIN_BUFFER_S + (self.MAX_BUFFER_S - self.MIN_BUFFER_S) * unavailability_factor

        # 4. Core decision logic based on slack.
        work_done = self._get_work_done()
        work_rem = self.task_duration - work_done

        # If the job is done, do nothing to save cost.
        if work_rem <= 0:
            return ClusterType.NONE

        time_now = self.env.elapsed_seconds
        time_rem_until_deadline = self.deadline - time_now

        # Slack is the extra time we have if we were to finish the rest of the
        # job using only On-Demand instances from now on.
        slack = time_rem_until_deadline - work_rem

        if slack < safety_buffer:
            # Slack is below our safety threshold; we must be conservative.
            # Use On-Demand to guarantee progress.
            return ClusterType.ON_DEMAND
        else:
            # We have enough slack; we can be aggressive to save cost.
            if has_spot:
                # Use cheap Spot instances when available.
                return ClusterType.SPOT
            else:
                # Wait for Spot to become available again, since we have time.
                return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser: argparse.ArgumentParser):
        """Required method for evaluator instantiation."""
        args, _ = parser.parse_known_args()
        return cls(args)
