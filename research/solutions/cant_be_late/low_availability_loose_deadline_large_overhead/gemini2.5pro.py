import math
from argparse import ArgumentParser

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    """
    This strategy operates on a few core principles to balance cost and completion risk:

    1.  **Safety First (Critical Region):** The primary goal is to never miss the deadline.
        We calculate a "point of no return" by determining the latest possible moment
        to switch to a reliable on-demand instance. If our current slack (time remaining
        minus work remaining) drops below a safety buffer, we enter a "critical region"
        and use on-demand exclusively to guarantee completion. The safety buffer is set
        to be a multiple of the restart overhead to account for potential time lost from
        spot preemptions.

    2.  **Opportunistic Spot Usage:** When not in the critical region, spot instances are
        always the preferred choice due to their low cost. If a spot instance is
        available, we will always use it.

    3.  **Adaptive Waiting (Linear Slack Scheduling):** If we are not in the critical
        region and spot is unavailable, we must decide whether to pay for an expensive
        on-demand instance or wait (at no cost) for a spot instance to become available.
        This decision is based on our progress relative to a "target schedule". This
        schedule is a straight line from the start of the job (0% work at time 0) to
        the deadline (100% work at deadline).
        - If our actual progress is *ahead* of this target schedule, we have a surplus of
          time and can afford to wait for a cheap spot instance, so we choose NONE.
        - If our progress is *behind* the target schedule, we are at risk of falling
          too far behind. We must use an on-demand instance to catch up.

    This three-tiered approach ensures we finish on time while aggressively pursuing
    cost savings when it is safe to do so. The strategy is adaptive, as prolonged
    periods of spot unavailability will naturally cause progress to fall behind the
    target, triggering on-demand usage to self-correct.
    """
    NAME = "adaptive_scheduler"  # REQUIRED: unique identifier

    def __init__(self, args):
        super().__init__(args)
        self.target_progress_rate = 0.0
        self.safety_buffer = 0.0
        self.work_done_cache = 0.0
        self.last_task_done_time_len = 0

    def solve(self, spec_path: str) -> "Solution":
        """
        Initializes the strategy's parameters based on the problem specification.
        This method is called once before the simulation begins.
        """
        # A baseline schedule is a linear completion of the task by the deadline.
        # This rate determines if we are "ahead" or "behind" schedule.
        if self.deadline > 0:
            self.target_progress_rate = self.task_duration / self.deadline
        else:
            self.target_progress_rate = 1.0

        # The safety buffer determines when to enter the "critical region".
        # We set it to twice the restart overhead to be conservative, accounting for
        # time lost from one preemption plus a margin for subsequent bad luck
        # (e.g., spot being unavailable immediately after a restart).
        self.safety_buffer = self.restart_overhead * 2.0

        # Initialize a cache for calculating completed work. This avoids
        # re-summing the entire list of work segments at every step.
        self.work_done_cache = 0.0
        self.last_task_done_time_len = 0
        
        return self

    def _update_work_done(self) -> float:
        """
        Efficiently calculates the total work done by caching the previous sum.
        """
        if len(self.task_done_time) > self.last_task_done_time_len:
            for i in range(self.last_task_done_time_len, len(self.task_done_time)):
                segment = self.task_done_time[i]
                self.work_done_cache += segment[1] - segment[0]
            self.last_task_done_time_len = len(self.task_done_time)
        return self.work_done_cache

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Core decision-making logic, called at each time step.
        """
        # Calculate current progress and remaining work/time.
        work_done = self._update_work_done()
        work_remaining = self.task_duration - work_done

        # If the job is finished, do nothing to avoid further costs.
        if work_remaining <= 0:
            return ClusterType.NONE

        elapsed_time = self.env.elapsed_seconds
        time_remaining = self.deadline - elapsed_time

        # --- I. CRITICAL REGION (FAIL-SAFE) ---
        # If the time required to finish on a reliable instance plus a safety margin
        # exceeds the time remaining, we must use on-demand to guarantee completion.
        if work_remaining + self.safety_buffer >= time_remaining:
            return ClusterType.ON_DEMAND

        # --- II. PREFERRED OPTION (SPOT) ---
        # If not in the critical region and spot is available, always use it.
        if has_spot:
            return ClusterType.SPOT

        # --- III. NO SPOT: TRADE-OFF (WAIT or PAY) ---
        # Decide between ON_DEMAND (catch up) and NONE (wait for spot).
        # We compare current progress to our linear target schedule.
        target_work_done = elapsed_time * self.target_progress_rate
        
        if work_done >= target_work_done:
            # We are ahead of or on schedule, so we can afford to wait.
            return ClusterType.NONE
        else:
            # We are behind schedule and must use on-demand to catch up.
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser: ArgumentParser):  # REQUIRED: For evaluator instantiation
        """
        Instantiates the strategy class from command-line arguments.
        """
        args, _ = parser.parse_known_args()
        return cls(args)