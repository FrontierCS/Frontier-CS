import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    """
    This strategy implements a "slack glidepath" approach to balance cost and
    deadline compliance. The core idea is to define a target amount of slack
    (time to deadline minus remaining work) that should be maintained at any
    given point in time. This target slack decreases linearly from the initial
    total slack (deadline - task_duration) to zero as the job progresses towards
    the deadline.

    The strategy operates in three zones based on the current slack relative
    to this target glidepath:

    1.  AHEAD ZONE (current_slack >= target_slack):
        The job is on or ahead of schedule. The strategy acts greedily to
        minimize cost, using Spot instances when available and waiting (NONE)
        when they are not, as it can afford to "burn" some of its surplus slack.

    2.  BEHIND ZONE (min_slack_threshold <= current_slack < target_slack):
        The job has fallen behind the target schedule. The strategy becomes more
        conservative. It still prioritizes cheap Spot instances if available, but
        if not, it switches to On-Demand to guarantee progress and prevent
        falling further behind. It is no longer willing to wait.

    3.  CRITICAL ZONE (current_slack < min_slack_threshold):
        The job's slack has dropped below a critical, absolute safety threshold
        (a multiple of the restart_overhead). In this "panic mode", the risk of
        a Spot preemption is too high, as it could cause a deadline failure.
        The strategy exclusively uses On-Demand instances to ensure completion.

    This multi-layered heuristic dynamically adapts its risk tolerance based on
    its progress, aiming to use the cheapest resources as much as possible while
    maintaining a robust safety margin to guarantee finishing on time.
    """
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        # A tunable hyperparameter. We enter "critical mode" if the remaining
        # slack is less than this many times the restart overhead. A factor of
        # 2.0 provides a buffer for at least two consecutive preemptions.
        min_slack_factor = 2.0

        # Pre-calculate constants for efficiency in the _step method.
        self.initial_slack = self.deadline - self.task_duration
        self.min_slack_threshold = min_slack_factor * self.restart_overhead

        # The linear decay rate of the target slack glidepath.
        if self.deadline > 0:
            self.slack_decay_rate = self.initial_slack / self.deadline
        else:
            self.slack_decay_rate = 0.0
            
        # Initialize caches for efficient calculation of work done.
        self.total_work_done_cache = 0.0
        self.last_num_segments_processed = 0
            
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Efficiently update the total work done by summing only new segments.
        num_segments = len(self.task_done_time)
        if num_segments > self.last_num_segments_processed:
            new_segments = self.task_done_time[self.last_num_segments_processed:]
            self.total_work_done_cache += sum(new_segments)
            self.last_num_segments_processed = num_segments
            
        total_work_done = self.total_work_done_cache
        remaining_work = self.task_duration - total_work_done

        # If the task is finished, do nothing to avoid further costs.
        if remaining_work <= 0:
            return ClusterType.NONE

        # Calculate current state variables.
        time_to_deadline = self.deadline - self.env.elapsed_seconds
        current_slack = time_to_deadline - remaining_work

        # Calculate the target slack for the current time using the linear glidepath.
        target_slack = self.initial_slack - self.env.elapsed_seconds * self.slack_decay_rate

        # --- Decision Logic ---

        # 1. CRITICAL ZONE: Absolute safety net.
        if current_slack < self.min_slack_threshold:
            return ClusterType.ON_DEMAND
        
        # 2. BEHIND ZONE: Behind the glidepath, need to catch up.
        elif current_slack < target_slack:
            if has_spot:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND
        
        # 3. AHEAD ZONE: On or ahead of the glidepath, can be greedy.
        else: # current_slack >= target_slack
            if has_spot:
                return ClusterType.SPOT
            else:
                return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)