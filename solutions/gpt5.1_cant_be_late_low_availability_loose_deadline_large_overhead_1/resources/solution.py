from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_safe_spot"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Compute remaining work
        if self.task_done_time:
            work_done = float(sum(self.task_done_time))
        else:
            work_done = 0.0
        remaining_work = max(0.0, float(self.task_duration) - work_done)

        # If task is done, no need to run more
        if remaining_work <= 0.0:
            return ClusterType.NONE

        current_time = float(self.env.elapsed_seconds)
        deadline = float(self.deadline)
        gap = float(self.env.gap_seconds)
        restart_overhead = float(self.restart_overhead)

        time_left = deadline - current_time

        # If somehow past deadline, just choose ON_DEMAND (environment likely handles failure)
        if time_left <= 0.0:
            return ClusterType.ON_DEMAND

        # Once we commit to ON_DEMAND, never go back to SPOT to avoid extra overhead/risk.
        if last_cluster_type == ClusterType.ON_DEMAND:
            return ClusterType.ON_DEMAND

        # Decide whether we can afford to wait/use SPOT for one more step.
        # Worst case this step: no progress, then we switch to ON_DEMAND next step and pay one restart overhead.
        # Require that even in that case we can still finish by the deadline.
        # Condition to safely *wait* (use SPOT/NONE this step):
        #   time_left_now >= remaining_work + restart_overhead + gap
        # If this is false, we must commit to ON_DEMAND now.
        can_wait_one_step = time_left >= (remaining_work + restart_overhead + gap)

        if not can_wait_one_step:
            # Commit to ON_DEMAND now to guarantee completion.
            return ClusterType.ON_DEMAND

        # We still have enough slack to explore cheaper options.
        # Prefer SPOT when available; otherwise, pause (NONE) to wait for SPOT.
        if has_spot:
            return ClusterType.SPOT
        else:
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
