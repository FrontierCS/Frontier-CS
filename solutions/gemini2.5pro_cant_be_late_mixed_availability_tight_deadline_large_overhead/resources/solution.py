import collections
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "adaptive_slack_v1"

    # --- Hyperparameters ---
    # The size of the rolling window for observing spot availability.
    HISTORY_SIZE = 240
    # Minimum assumed spot availability probability to avoid division by zero.
    P_MIN = 0.05
    # Slack threshold for "panic mode" as a multiple of restart overhead.
    PANIC_SLACK_OVERHEAD_FACTOR = 1.5
    # Base slack threshold for waiting, as a multiple of restart overhead.
    BASE_WAIT_SLACK_OVERHEAD_FACTOR = 3.0
    # Safety multiplier for the adaptive part of the wait threshold.
    ADAPTIVE_WAIT_SAFETY_FACTOR = 2.0
    
    def solve(self, spec_path: str) -> "Solution":
        """
        Initializes the strategy. Called once before each evaluation trace.
        """
        # Initialize a deque to store the recent history of spot availability.
        self.spot_history = collections.deque(maxlen=self.HISTORY_SIZE)
        
        # Pre-populate history with a neutral 50% availability assumption.
        half_history = self.HISTORY_SIZE // 2
        self.spot_history.extend([1] * half_history)
        self.spot_history.extend([0] * (self.HISTORY_SIZE - half_history))
        
        # Pre-calculate the static panic threshold in seconds.
        self._panic_slack_threshold_seconds = self.restart_overhead * self.PANIC_SLACK_OVERHEAD_FACTOR
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Main decision-making function, called at each time step.
        """
        # 1. Update State: Record current spot availability.
        self.spot_history.append(1 if has_spot else 0)
        
        # 2. Calculate Key Metrics
        work_left = self.remaining_work_seconds

        # If the task is completed, do nothing.
        if work_left <= 0:
            return ClusterType.NONE

        time_left = self.deadline - self.env.elapsed_seconds
        current_slack = time_left - work_left

        # 3. Decision Logic
        # Panic Zone: If slack is critically low, use On-Demand to guarantee progress.
        if current_slack <= self._panic_slack_threshold_seconds:
            return ClusterType.ON_DEMAND

        # Not in panic mode, so we have some slack.
        if has_spot:
            # Always prefer the cheaper Spot instance when available.
            return ClusterType.SPOT
        else:
            # Spot not available. Decide between On-Demand (costly) or None (spends slack).
            # This choice is based on an adaptive threshold.
            
            # Estimate spot availability from recent history.
            p_spot = sum(self.spot_history) / len(self.spot_history)
            p_safe = max(p_spot, self.P_MIN)

            # The adaptive component is based on the expected wait time for a spot instance.
            adaptive_wait_component = (
                (1 / p_safe - 1) * 
                self.env.gap_seconds * 
                self.ADAPTIVE_WAIT_SAFETY_FACTOR
            )
            
            # The base component is a fixed buffer for absorbing preemptions.
            base_wait_component = self.restart_overhead * self.BASE_WAIT_SLACK_OVERHEAD_FACTOR
            
            wait_threshold_seconds = base_wait_component + adaptive_wait_component

            if current_slack > wait_threshold_seconds:
                # Comfort Zone: Slack is high enough to wait for a Spot instance.
                return ClusterType.NONE
            else:
                # Buffer Zone: Slack is too low to risk waiting. Use On-Demand.
                return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        """
        Required classmethod for evaluator instantiation.
        """
        args, _ = parser.parse_known_args()
        return cls(args)
