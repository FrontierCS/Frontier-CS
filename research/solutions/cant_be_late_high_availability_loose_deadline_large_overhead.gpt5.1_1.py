from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "safe_spot_od_deadline_strategy_v1"

    def __init__(self, args):
        super().__init__(args)

    def solve(self, spec_path: str) -> "Solution":
        # No pre-processing needed; parameters are available via self.env during simulation.
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If environment is not yet fully initialized, default to safest option: ON_DEMAND.
        # This should practically never happen during evaluation, but keeps code robust.
        if not hasattr(self, "env") or self.env is None:
            return ClusterType.ON_DEMAND

        env = self.env
        gap = getattr(env, "gap_seconds", 0.0)
        elapsed = getattr(env, "elapsed_seconds", 0.0)
        deadline = getattr(self, "deadline", float("inf"))
        task_duration = getattr(self, "task_duration", 0.0)
        restart_overhead = getattr(self, "restart_overhead", 0.0)

        # Compute how much work has been completed.
        # We assume each completed work segment corresponds to gap seconds of work.
        task_done_time = getattr(self, "task_done_time", None)
        if task_done_time is None:
            work_done = 0.0
        else:
            work_done = len(task_done_time) * gap

        remaining_work = max(task_duration - work_done, 0.0)
        time_left = deadline - elapsed

        # If the task is done or we're out of time, avoid unnecessary cost.
        if remaining_work <= 0.0:
            return ClusterType.NONE

        if time_left <= 0.0:
            # Already past deadline; run ON_DEMAND to minimize further damage.
            return ClusterType.ON_DEMAND

        # Safety condition:
        # We are allowed to "risk" this step on SPOT (or idle) only if,
        # even in the worst case of:
        #   - zero useful work this step (loss of `gap` seconds), and
        #   - up to `restart_overhead` seconds overhead when we finally switch to ON_DEMAND,
        # we can still finish by the deadline by running ON_DEMAND afterwards.
        #
        # That requires:
        #   remaining_work + restart_overhead <= time_left - gap
        # <=> remaining_work <= time_left - (gap + restart_overhead)
        safe_to_wait = remaining_work <= (time_left - (gap + restart_overhead))

        if not safe_to_wait:
            # We are close enough to the deadline that we must use guaranteed progress.
            return ClusterType.ON_DEMAND

        # We have sufficient slack.
        # Prefer SPOT when available (cheaper), otherwise pause to save cost.
        if has_spot:
            return ClusterType.SPOT

        # No spot available and we have slack: pause instead of using expensive ON_DEMAND.
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)