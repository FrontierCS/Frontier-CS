import argparse

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    """
    A strategy that uses a buffer-based, three-tiered approach to decide
    which cluster type to use. The core idea is to calculate a "safety buffer"
    which represents the amount of time that can be wasted before the deadline
    becomes unreachable even when using reliable on-demand instances.

    The strategy operates in three modes based on the size of this buffer:
    1. PANIC MODE: Buffer is critically low. Force the use of ON_DEMAND to
       guarantee progress and avoid failing the task.
    2. RELAXED MODE: Buffer is very large. Prioritize cost savings by using
       SPOT when available, and waiting (NONE) if it's not.
    3. CAUTIOUS MODE: Buffer is in between. Use SPOT if available, but if not,
       use ON_DEMAND to avoid eroding the buffer too much by waiting.

    The thresholds for these modes are defined as multiples of the restart
    overhead, making the strategy adaptive to the specific penalty of the task.
    """
    NAME = "my_solution"

    # If safety_buffer < RISK_MULTIPLIER * restart_overhead, use ON_DEMAND.
    # This value is chosen to be enough to withstand a couple of preemptions
    # without making the deadline unreachable.
    RISK_MULTIPLIER = 2.5

    # If spot is unavailable and safety_buffer >= WAIT_MULTIPLIER * restart_overhead,
    # wait (NONE). Otherwise, use ON_DEMAND. This value is based on the
    # initial slack, representing a significant portion of it (half).
    WAIT_MULTIPLIER = 10.0

    def solve(self, spec_path: str):
        """
        Optional initialization. Called once before evaluation.
        No pre-computation is needed for this strategy.
        Must return self.
        """
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
        # 1. Calculate current state
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done

        # If the task is finished, do nothing to save costs.
        if work_remaining <= 0:
            return ClusterType.NONE

        time_left = self.deadline - self.env.elapsed_seconds

        # The safety buffer is the slack time we have if we were to finish all
        # remaining work using only reliable ON_DEMAND instances.
        safety_buffer = time_left - work_remaining

        # Define the thresholds based on the restart overhead.
        risk_threshold = self.RISK_MULTIPLIER * self.restart_overhead
        wait_threshold = self.WAIT_MULTIPLIER * self.restart_overhead

        # --- Three-tiered decision logic ---

        # 1. PANIC MODE: Buffer is critically low.
        # We are at risk of missing the deadline. Must use the most reliable
        # option to guarantee progress.
        if safety_buffer < risk_threshold:
            return ClusterType.ON_DEMAND

        # 2. DEFAULT CHOICE: If not in panic mode, try to use cheap SPOT.
        if has_spot:
            return ClusterType.SPOT

        # 3. SPOT UNAVAILABLE: Decide between waiting (NONE) or paying for
        # ON_DEMAND. This decision is based on the size of our safety buffer.

        # CAUTIOUS MODE: Buffer is not large enough to wait idly.
        # Use ON_DEMAND to ensure we keep making progress.
        if safety_buffer < wait_threshold:
            return ClusterType.ON_DEMAND
        
        # RELAXED MODE: We have a large buffer. We can afford to wait
        # for SPOT to become available again, saving money.
        else:
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        """
        Required classmethod for evaluator instantiation.
        """
        args, _ = parser.parse_known_args()
        return cls(args)
