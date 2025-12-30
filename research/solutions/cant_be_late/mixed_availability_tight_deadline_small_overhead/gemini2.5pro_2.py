import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    """
    A strategy for the Cant-Be-Late Scheduling Problem that balances cost and
    the risk of missing the deadline.

    The strategy operates in three zones based on the current "slack" time,
    which is the buffer between the projected finish time (if using reliable
    On-Demand instances) and the hard deadline.

    - CRITICAL ZONE: If slack is very low (below `critical_slack_threshold`),
      the strategy exclusively uses On-Demand instances to guarantee completion
      and avoid the -100000 penalty.

    - CAUTIOUS ZONE: If slack is moderate (below `cautious_slack_threshold`),
      the strategy uses Spot instances if available, but falls back to
      On-Demand otherwise. This prevents wasting slack by waiting.

    - SAFE ZONE: If there is ample slack, the strategy is more aggressive in
      cost-saving. It uses Spot when available and chooses to wait (NONE)
      if Spot is unavailable, preserving money at the cost of consuming slack.

    Thresholds are calculated once in the `solve` method based on the specific
    parameters of the task (initial slack, restart overhead).
    """
    NAME = "my_solution"

    def __init__(self, args: argparse.Namespace):
        super().__init__(args)
        # Internal state for tracking progress efficiently
        self._work_done: float = 0.0
        self._last_len_task_done_time: int = 0
        
        # Thresholds for the three zones, to be initialized in solve()
        self.critical_slack_threshold: float = 0.0
        self.cautious_slack_threshold: float = 0.0

    def solve(self, spec_path: str) -> "Solution":
        """
        Initializes the strategy's thresholds based on the problem specification.
        This method is called once before the simulation starts.
        """
        # Calculate the total initial slack time available.
        initial_slack = self.deadline - self.task_duration

        # Set the threshold for the "cautious" zone.
        # We define this as a fraction of the initial slack. If slack falls
        # below this, we stop waiting and use On-Demand to make progress.
        self.cautious_slack_threshold = 0.5 * initial_slack

        # Set the threshold for the "critical" zone.
        # This is a hard safety buffer. It's calculated to be large enough to
        # withstand a configurable number of consecutive preemptions.
        # The time cost of one preemption includes the lost work time (gap_seconds)
        # and the restart overhead.
        preemption_time_cost = self.restart_overhead + self.env.gap_seconds
        num_preemptions_buffer = 5
        self.critical_slack_threshold = num_preemptions_buffer * preemption_time_cost
        
        return self

    def _update_work_done(self) -> None:
        """
        Efficiently updates the total work done by only summing new segments
        from self.task_done_time, avoiding re-computation.
        """
        num_done_segments = len(self.task_done_time)
        if num_done_segments > self._last_len_task_done_time:
            new_segments = self.task_done_time[self._last_len_task_done_time:]
            self._work_done += sum(end - start for start, end in new_segments)
            self._last_len_task_done_time = num_done_segments

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        The main decision-making logic, called at each time step.
        """
        self._update_work_done()
        
        work_remaining = self.task_duration - self._work_done
        # If the job is finished, we don't need any cluster.
        if work_remaining <= 0.0:
            return ClusterType.NONE

        time_to_deadline = self.deadline - self.env.elapsed_seconds
        
        # Slack is the time buffer we have. If we ran on On-Demand from now on,
        # we would finish this many seconds before the deadline.
        current_slack = time_to_deadline - work_remaining

        # --- Decision Logic based on three zones ---
        
        # 1. CRITICAL ZONE: If slack is below the safety buffer, we must use
        #    On-Demand to ensure we finish. This is the highest priority rule.
        if current_slack <= self.critical_slack_threshold:
            return ClusterType.ON_DEMAND

        # 2. OPPORTUNISTIC SPOT: If we are not in the critical zone and Spot
        #    instances are available, always use them for maximum cost savings.
        if has_spot:
            return ClusterType.SPOT

        # At this point, we are not critical, but Spot is unavailable.
        # The decision is between waiting (NONE) and paying for On-Demand.
        
        # 3. CAUTIOUS ZONE: If slack is below the cautious threshold, we can't
        #    afford to wait and lose more slack. We use On-Demand to make progress.
        if current_slack <= self.cautious_slack_threshold:
            return ClusterType.ON_DEMAND
        
        # 4. SAFE ZONE: If we have plenty of slack, we can afford to wait for a
        #    cheap Spot instance to become available. We do nothing this step.
        else:
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser: argparse.ArgumentParser) -> "Solution":
        """
        Instantiates the strategy from command-line arguments.
        This strategy does not require any custom arguments.
        """
        args, _ = parser.parse_known_args()
        return cls(args)