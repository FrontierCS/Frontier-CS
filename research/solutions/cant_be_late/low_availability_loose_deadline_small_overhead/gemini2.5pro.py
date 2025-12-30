import argparse

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    """
    A strategy based on maintaining a "safety margin" or "slack".

    The core idea is to define the slack as the amount of time we can afford to
    waste before we risk missing the deadline, assuming all remaining work is
    done on reliable On-Demand instances.

    Slack = (Time remaining until deadline) - (Time needed to finish on On-Demand)

    The strategy has two main modes:
    1.  **Slack-burning mode:** When the slack is high (above a threshold), the
        strategy is optimistic. It uses cheap Spot instances when available. If
        Spot is not available, it chooses to wait (NONE), effectively "burning"
        slack in the hope that Spot will become available soon.

    2.  **Slack-preserving mode:** When the slack drops below the threshold, the
        strategy becomes conservative. It still prioritizes the cheap Spot
        instances when available. However, if Spot is unavailable, it switches
        to expensive On-Demand instances instead of waiting. Using On-Demand
        makes progress at the same rate time passes, thus preserving the
        remaining slack. This acts as a safety net to prevent falling further
        behind schedule.

    A "panic mode" ensures that if the slack becomes negative (meaning we are
    projected to miss the deadline even with 100% On-Demand usage), the
    strategy will always choose On-Demand to minimize the delay.

    The threshold is chosen as a fraction of the total initial slack, making
    the strategy adaptive to different task durations and deadlines.
    """
    NAME = "slack_preserver_strategy"  # REQUIRED: unique identifier

    # This fraction determines how much of the initial slack we are willing to
    # "burn" waiting for Spot instances before switching to a conservative,
    # slack-preserving mode. A higher value means being more conservative.
    # Given the low and variable spot availability (4-40%), a reasonably
    # high fraction is chosen to build a robust buffer against long droughts.
    SLACK_FRACTION_THRESHOLD = 0.35

    def __init__(self, args, env=None):
        super().__init__(args, env)
        self._initialized = False
        self.wait_threshold = 0

    def solve(self, spec_path: str) -> "Solution":
        """
        Optional initialization. Called once before evaluation.
        Must return self.
        """
        # Initialization is done lazily in the first call to _step()
        # to ensure all environment attributes are available.
        return self

    def _initialize_strategy(self):
        """
        Initializes strategy parameters on the first step.
        """
        initial_slack = self.deadline - self.task_duration
        self.wait_threshold = initial_slack * self.SLACK_FRACTION_THRESHOLD
        self._initialized = True

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Called at each time step. Return which cluster type to use next.
        """
        if not self._initialized:
            self._initialize_strategy()

        # 1. Calculate current progress and remaining work.
        # We assume `task_done_time` is the most reliable source of truth for
        # completed work. The potential inaccuracy from not counting a currently
        # in-progress segment is small over the long horizon of the task.
        # This is also a conservative estimate, making the strategy safer.
        work_done = sum(end - start for start, end in self.task_done_time)
        work_remaining = self.task_duration - work_done

        # If the task is finished, do nothing.
        if work_remaining <= 0:
            return ClusterType.NONE

        # 2. Calculate time remaining and the safety margin (slack).
        time_now = self.env.elapsed_seconds
        time_remaining = self.deadline - time_now
        
        # Safety margin is the key metric: how much time can we waste
        # and still finish on time using On-Demand for the rest of the way.
        safety_margin = time_remaining - work_remaining

        # 3. Decision Logic.

        # PANIC MODE: If the safety margin is less than a single time step,
        # we are projected to fail. We must use On-Demand to make progress.
        # This is the ultimate safety net.
        if safety_margin < self.env.gap_seconds:
            return ClusterType.ON_DEMAND

        # ALWAYS-SPOT RULE: If Spot instances are available, always use them.
        # A successful Spot step is as productive as On-Demand but much cheaper.
        # The risk of preemption is managed by our safety margin buffer.
        # There's no scenario where On-Demand is better than an available Spot.
        if has_spot:
            return ClusterType.SPOT
        
        # NO-SPOT DECISION: Spot is not available.
        # We must choose between waiting (NONE) and paying for progress (ON_DEMAND).
        if safety_margin > self.wait_threshold:
            # SLACK-BURNING MODE: We have a comfortable safety margin,
            # so we can afford to wait for a cheap Spot instance to appear.
            # This consumes slack but saves money.
            return ClusterType.NONE
        else:
            # SLACK-PRESERVING MODE: Our safety margin is below the threshold.
            # We can no longer afford to wait and burn more slack. We must
            # use On-Demand to guarantee progress and preserve our remaining
            # safety margin. This buffer is now reserved to absorb future
            # Spot preemptions or short droughts.
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser: argparse.ArgumentParser) -> "Solution":
        """
        REQUIRED: For evaluator instantiation.
        """
        args, _ = parser.parse_known_args()
        return cls(args)