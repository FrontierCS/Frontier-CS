import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    """
    This strategy uses a dynamic, slack-based heuristic to decide which cluster type to use.

    The core idea is to operate in one of two modes: "Gamble" or "Safe".

    - "Gamble" Mode:
        - Activated when there is sufficient slack time.
        - Prioritizes cost savings by using Spot instances when available.
        - If Spot is not available, it waits (NONE) for it to become available, consuming slack.

    - "Safe" Mode:
        - Activated when slack time is low.
        - Prioritizes job completion by using reliable On-Demand instances.

    The decision boundary between these modes is determined by a "risk threshold". This
    threshold is dynamically adjusted based on job progress:
    
    - At the start of the job, the threshold is lower, making the strategy more
      aggressive in seeking cheap Spot resources.
    - As the job progresses, the threshold increases, making the strategy more
      conservative to ensure it meets the deadline.

    The threshold is defined as `k * restart_overhead`, where `k` is a factor that
    grows linearly with job completion percentage. This ensures that as less time
    remains, we become increasingly unwilling to risk a time-consuming preemption.

    To maintain performance, the total work completed is cached and updated incrementally,
    avoiding redundant calculations at each step.
    """
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        # Tunable parameters for the risk threshold factor 'k'.
        # We become more risk-averse (require a larger k) as the job progresses.
        # k starts at k_start and linearly interpolates to k_end.
        self.k_start = 1.1
        self.k_end = 2.0

        # Cache for work_done calculation to improve performance.
        self._work_done_cache = 0.0
        self._last_task_done_time_len = 0
        return self

    def _get_work_done(self) -> float:
        """
        Calculates the total work done so far, using a cache to avoid
        re-summing the entire list at every step. This assumes that
        self.task_done_time is an append-only list.
        """
        if len(self.task_done_time) > self._last_task_done_time_len:
            new_segments = self.task_done_time[self._last_task_done_time_len:]
            self._work_done_cache += sum(end - start for start, end in new_segments)
            self._last_task_done_time_len = len(self.task_done_time)
        return self._work_done_cache

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        work_done = self._get_work_done()
        work_remaining = self.task_duration - work_done
        
        # If the job is finished, do nothing to save cost.
        if work_remaining <= 1e-6:
            return ClusterType.NONE

        time_now = self.env.elapsed_seconds
        
        # Slack is the buffer time we have before the deadline, assuming
        # we run the rest of the job on a reliable (on-demand) instance.
        slack = self.deadline - time_now - work_remaining

        # Determine a dynamic risk threshold. We become more conservative
        # (require more slack) as the job nears completion.
        if self.task_duration > 0:
            progress_fraction = work_done / self.task_duration
            # Clamp progress_fraction to be robust.
            progress_fraction = max(0.0, min(1.0, progress_fraction))
        else:
            progress_fraction = 1.0

        k = self.k_start + (self.k_end - self.k_start) * progress_fraction
        risk_threshold = k * self.restart_overhead

        # --- Decision Logic ---
        # If our slack is greater than the risk threshold, we can afford to
        # gamble on cheaper Spot instances. Otherwise, we must play it safe.
        if slack > risk_threshold:
            # "Gamble" mode: Use Spot if available, otherwise wait.
            if has_spot:
                return ClusterType.SPOT
            else:
                return ClusterType.NONE
        else:
            # "Safe" mode: Use reliable On-Demand to guarantee progress.
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
