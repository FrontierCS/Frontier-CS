import collections
from argparse import ArgumentParser

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "deadline_aware_adaptive_strategy"

    def __init__(self, args):
        super().__init__(args)
        # --- Strategy Parameters ---
        # Lookback window for estimating spot availability
        self.HISTORY_WINDOW = 120
        # Safety buffer as a multiple of restart overhead
        self.BUFFER_FACTOR = 2.5
        # Probability threshold for waiting when slack is high
        self.THRESHOLD_LOW = 0.05
        # Probability threshold for waiting when slack is low
        self.THRESHOLD_HIGH = 0.50

        # --- Internal State ---
        self.remaining_overhead: float = 0.0
        self.spot_history: collections.deque = collections.deque(maxlen=self.HISTORY_WINDOW)
        self.initial_slack: float = 0.0
        self.safety_buffer: float = 0.0
        self.is_initialized: bool = False

    def solve(self, spec_path: str) -> "Solution":
        """
        Optional initialization. Called once before evaluation.
        """
        return self

    def _initialize(self):
        """
        Lazy one-time initialization, called on the first _step,
        when environment attributes are available.
        """
        self.initial_slack = self.deadline - self.task_duration
        self.safety_buffer = self.restart_overhead * self.BUFFER_FACTOR
        self.is_initialized = True

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Called at each time step. Return which cluster type to use next.
        """
        if not self.is_initialized:
            self._initialize()

        time_now = self.env.elapsed_seconds
        gap = self.env.gap_seconds

        # Update overhead based on preemption in the last step
        is_preempted = (last_cluster_type == ClusterType.SPOT and not has_spot)
        if is_preempted:
            self.remaining_overhead = self.restart_overhead
        else:
            self.remaining_overhead = max(0.0, self.remaining_overhead - gap)

        # Update history for spot availability estimation
        self.spot_history.append(1 if has_spot else 0)
        
        work_remaining = self.task_duration - self.work_done
        
        if work_remaining <= 0:
            return ClusterType.NONE

        # Calculate time needed for a guaranteed finish on On-Demand
        time_remaining_to_deadline = self.deadline - time_now
        time_needed_for_od_finish = work_remaining + self.remaining_overhead
        
        # If remaining time is less than needed for a safe OD finish, we must use OD.
        if time_remaining_to_deadline <= time_needed_for_od_finish + self.safety_buffer:
            return ClusterType.ON_DEMAND
        
        # If we have slack and spot is available, use it greedily.
        if has_spot:
            return ClusterType.SPOT
        
        # If spot is not available, decide between waiting (NONE) or using ON_DEMAND.
        # Estimate spot availability probability from recent history.
        if len(self.spot_history) > 0:
            p_spot = sum(self.spot_history) / len(self.spot_history)
        else:
            p_spot = 0.5  # Initial guess

        # Calculate current slack beyond the safety buffer
        current_slack = time_remaining_to_deadline - (time_needed_for_od_finish + self.safety_buffer)
        
        # Set a dynamic threshold based on available slack. More slack -> more risk-taking.
        if self.initial_slack > 0:
            slack_ratio = min(1.0, max(0.0, current_slack / self.initial_slack))
            threshold = self.THRESHOLD_HIGH - slack_ratio * (self.THRESHOLD_HIGH - self.THRESHOLD_LOW)
        else:
            threshold = self.THRESHOLD_HIGH
        
        if p_spot >= threshold:
            # High chance of spot, or lots of slack -> wait.
            return ClusterType.NONE
        else:
            # Low chance of spot, or little slack -> use ON_DEMAND to make progress.
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        """
        Required classmethod for evaluator instantiation.
        """
        args, _ = parser.parse_known_args()
        return cls(args)