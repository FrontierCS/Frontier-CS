import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args):
        super().__init__(args)
        # This strategy uses a 3-zone policy based on "effective slack".
        # Effective slack is the time buffer we have if we were to switch
        # to reliable on-demand instances right now to finish the job.

        # Zone 1: Critical (Safety Margin)
        # If effective slack drops below this, we switch to on-demand permanently.
        # This is a final safety buffer to guarantee finishing before the deadline.
        # Value: 30 minutes
        self.safety_margin = 1800

        # Zone 2: Caution (Wait Threshold)
        # If effective slack is above the safety margin but below this threshold,
        # we are in a caution zone. We use spot if available, but fall back to
        # on-demand if not, as we can't afford to waste too much time waiting.
        # Value: 2 hours
        self.wait_threshold = 7200

        # Zone 3: Safe
        # If effective slack is above the wait threshold, we have plenty of time.
        # We use spot if available, and wait (NONE) if it's not, to save costs.

        self.force_on_demand = False

    def solve(self, spec_path: str) -> "Solution":
        """
        Optional initialization. Called once before evaluation.
        """
        self.force_on_demand = False
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Called at each time step. Return which cluster type to use next.
        """
        if self.force_on_demand:
            return ClusterType.ON_DEMAND

        work_done = sum(end - start for start, end in self.task_done_time)
        work_left = self.task_duration - work_done

        if work_left <= 0:
            return ClusterType.NONE

        time_left_to_deadline = self.deadline - self.env.elapsed_seconds
        
        # Calculate the worst-case time needed to finish using only on-demand.
        # This assumes we might have just been preempted, incurring one restart overhead.
        time_needed_on_demand = work_left + self.restart_overhead
        
        # Calculate the real buffer we have against this worst-case scenario.
        effective_slack = time_left_to_deadline - time_needed_on_demand

        # --- 3-Zone Decision Logic ---

        # Zone 1: Critical
        if effective_slack <= self.safety_margin:
            self.force_on_demand = True
            return ClusterType.ON_DEMAND

        # If not in critical zone, try to use spot if available.
        if has_spot:
            return ClusterType.SPOT

        # If spot is not available, decide based on which zone we are in.
        # Zone 2: Caution
        if effective_slack <= self.wait_threshold:
            return ClusterType.ON_DEMAND
        # Zone 3: Safe
        else:
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        """
        For evaluator instantiation.
        """
        args, _ = parser.parse_known_args()
        return cls(args)