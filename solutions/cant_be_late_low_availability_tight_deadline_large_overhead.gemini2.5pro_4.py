import collections
import argparse

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    """
    This strategy employs a multi-layered heuristic to balance cost and completion risk.

    1.  **Panic Mode:** A primary, conservative check determines if the job is at immediate risk of
        failing to meet the deadline. If the time remaining is less than the work remaining plus
        the overhead of one potential spot instance preemption, the strategy switches to guaranteed
        On-Demand instances to ensure completion. This acts as a critical safety net.

    2.  **Availability-Aware Spot Usage:** When not in panic mode, the strategy estimates the recent
        spot instance availability using a sliding window of past observations. It will only choose
        to use a spot instance if the estimated availability is above a certain threshold. This
        threshold is set higher than the simple cost-benefit breakeven point to account for
        the time cost of restart overheads. If spot is available but the estimated
        availability is too low, the strategy conservatively uses On-Demand to avoid the high risk
        of preemption.

    3.  **Slack-Based Waiting:** If spot instances are not available, the strategy must decide between
        incurring cost to make progress with On-Demand or waiting for spot to become available
        (at no cost). This decision is based on the current "slack time" (the difference between
        the time remaining to deadline and the work remaining). If the slack is above a configured
        threshold, the strategy chooses to wait. If the slack is dwindling, it opts to use On-Demand
        to avoid falling behind schedule.
    """
    NAME = "AdaptiveHybrid"

    # The number of past time steps to consider for estimating spot availability.
    HISTORY_WINDOW_SIZE = 120

    # The minimum estimated spot availability required to choose SPOT over ON_DEMAND.
    # Spot/On-Demand price ratio is ~0.32. This is higher to be conservative.
    AVAILABILITY_THRESHOLD = 0.40

    # Slack threshold for waiting (vs using OD) as a multiple of restart_overhead.
    WAIT_SLACK_FACTOR = 3.0

    def solve(self, spec_path: str) -> "Solution":
        """
        Initializes the strategy's state before the simulation begins.
        """
        self.history = collections.deque(maxlen=self.HISTORY_WINDOW_SIZE)
        self.spot_seen = 0
        self.spot_available = 0

        # Pre-calculate the slack threshold in seconds for the waiting decision.
        self.wait_threshold_seconds = self.WAIT_SLACK_FACTOR * self.restart_overhead
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Makes a decision at each time step of the simulation.
        """
        # 1. Update Availability Estimate
        self.spot_seen += 1
        self.history.append(1 if has_spot else 0)
        if has_spot:
            self.spot_available += 1
        
        # Use a cumulative average until the window is full for stability,
        # then a sliding window for responsiveness.
        if self.spot_seen < self.HISTORY_WINDOW_SIZE:
            # Assume 50% availability if we have no data yet.
            availability = self.spot_available / self.spot_seen if self.spot_seen > 0 else 0.5
        else:
            availability = sum(self.history) / self.HISTORY_WINDOW_SIZE

        # 2. Calculate Current Progress and Time
        work_done = sum(end - start for start, end in self.task_done_time)
        work_rem = self.task_duration - work_done
        
        if work_rem <= 0:
            return ClusterType.NONE

        time_now = self.env.elapsed_seconds
        time_rem = self.deadline - time_now
        
        if time_rem <= 0:
             return ClusterType.ON_DEMAND

        # 3. PANIC MODE: Must use On-Demand to guarantee completion.
        # This triggers if a single spot preemption would make it impossible to finish.
        if work_rem >= time_rem - self.restart_overhead:
            return ClusterType.ON_DEMAND
            
        # 4. STANDARD DECISION LOGIC
        if has_spot:
            # Spot is available. Use if availability is high enough to be worth the risk.
            if availability >= self.AVAILABILITY_THRESHOLD:
                return ClusterType.SPOT
            else:
                # Availability is too low; use reliable On-Demand.
                return ClusterType.ON_DEMAND
        else:
            # Spot not available. Wait (NONE) or work (ON_DEMAND)?
            # Decision is based on how much slack time we have.
            total_slack = time_rem - work_rem
            if total_slack > self.wait_threshold_seconds:
                # Plenty of slack, can afford to wait.
                return ClusterType.NONE
            else:
                # Slack is low, better make progress with On-Demand.
                return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        """
        Required classmethod to instantiate the strategy from command-line arguments.
        """
        args, _ = parser.parse_known_args()
        return cls(args)
