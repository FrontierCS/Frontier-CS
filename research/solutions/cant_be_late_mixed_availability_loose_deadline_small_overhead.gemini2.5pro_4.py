import collections
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    """
    An adaptive strategy that makes decisions based on the remaining "slack".
    Slack is the time buffer beyond the minimum time required to finish the
    job using reliable on-demand instances.

    The core logic is a three-tiered approach:
    1. High Slack: Aggressively use Spot instances. If unavailable, wait (NONE)
       to minimize cost, betting on Spot becoming available soon. This behavior
       is modulated by recent spot availability history.
    2. Medium Slack: Cautiously use Spot. If unavailable, switch to On-Demand to
       ensure progress, as waiting becomes too risky.
    3. Low Slack (Emergency): Exclusively use On-Demand to guarantee completion
       before the deadline.
    """
    NAME = "adaptive_slack_strategy"

    def solve(self, spec_path: str) -> "Solution":
        # --- Strategy Parameters ---

        # Safety buffer is slack we reserve for emergencies (e.g., preemptions).
        # If current_slack falls below this, we switch to ON_DEMAND exclusively.
        # It's dynamic: a fraction of remaining work + a constant minimum.
        self.SAFETY_SLACK_FACTOR = 0.1
        self.MIN_SAFETY_RESTARTS = 2.0

        # When spot is unavailable, we decide whether to wait (NONE) or use ON_DEMAND.
        # This threshold is based on slack, measured in hours.
        self.WAIT_SLACK_BASE_H = 8.0
        # If spot has been highly available recently, we are more willing to wait.
        self.WAIT_SLACK_BONUS_H = 4.0
        
        # History tracking parameters to measure recent spot availability.
        self.HISTORY_WINDOW = 120
        self.HIGH_AVAIL_THRESHOLD = 0.8

        # --- Internal State ---
        self.spot_history = collections.deque(maxlen=self.HISTORY_WINDOW)
        self.work_done_cache = {'time': -1, 'value': 0.0}
        
        return self

    def _get_work_done(self) -> float:
        """Calculates and caches the total work completed to avoid re-summing."""
        current_time = self.env.elapsed_seconds
        if self.work_done_cache['time'] != current_time:
            work_done = sum(end - start for start, end in self.task_done_time)
            self.work_done_cache = {'time': current_time, 'value': work_done}
        return self.work_done_cache['value']

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """Main decision logic for each time step."""
        self.spot_history.append(1 if has_spot else 0)
        
        work_done = self._get_work_done()
        work_remaining = self.task_duration - work_done

        if work_remaining <= 1e-9:
            return ClusterType.NONE  # Job is finished

        time_remaining_to_deadline = self.deadline - self.env.elapsed_seconds
        current_slack = time_remaining_to_deadline - work_remaining

        # 1. Safety Check: If slack is critically low, use On-Demand.
        safety_slack_threshold = (work_remaining * self.SAFETY_SLACK_FACTOR +
                                  self.MIN_SAFETY_RESTARTS * self.restart_overhead)
        if current_slack <= safety_slack_threshold:
            return ClusterType.ON_DEMAND

        # 2. Primary Choice: Use cheap Spot instances if available.
        if has_spot:
            return ClusterType.SPOT

        # 3. Fallback: Spot is unavailable. Decide whether to wait or use On-Demand.
        wait_slack_threshold_h = self.WAIT_SLACK_BASE_H
        if len(self.spot_history) == self.HISTORY_WINDOW:
            recent_availability = sum(self.spot_history) / self.HISTORY_WINDOW
            if recent_availability >= self.HIGH_AVAIL_THRESHOLD:
                # If spot has been reliable, we're willing to wait longer for it.
                wait_slack_threshold_h += self.WAIT_SLACK_BONUS_H
        
        wait_slack_threshold_s = wait_slack_threshold_h * 3600.0

        if current_slack > wait_slack_threshold_s:
            # Plenty of slack, we can afford to wait for Spot.
            return ClusterType.NONE
        else:
            # Slack is shrinking, we must make progress with On-Demand.
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)