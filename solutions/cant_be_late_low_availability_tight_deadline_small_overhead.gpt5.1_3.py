from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args):
        super().__init__(args)
        self.args = args
        self._lock_on_od = False
        self._initialized_custom = False
        self._safety_margin = 0.0

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _init_policy_if_needed(self):
        if self._initialized_custom:
            return

        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        restart_overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        try:
            max_slack = float(self.deadline - self.task_duration)
        except Exception:
            max_slack = 0.0

        if max_slack <= 0.0:
            base_margin = restart_overhead * 2.0 + gap * 2.0
        else:
            base_margin = max(
                0.1 * max_slack,  # keep 10% of slack as buffer
                restart_overhead * 2.0,
                gap * 3.0,
            )

        if base_margin < gap:
            base_margin = gap

        self._safety_margin = base_margin
        self._initialized_custom = True

    def _compute_work_done(self) -> float:
        td = getattr(self, "task_done_time", None)
        if td is None:
            return 0.0
        if isinstance(td, (list, tuple)):
            return float(sum(td))
        try:
            return float(td)
        except Exception:
            return 0.0

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._init_policy_if_needed()

        work_done = self._compute_work_done()
        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        remaining_work = task_duration - work_done

        if remaining_work <= 0.0:
            return ClusterType.NONE

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        remaining_wall = deadline - elapsed

        if remaining_wall <= 0.0:
            self._lock_on_od = True
            return ClusterType.ON_DEMAND

        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        restart_overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        time_needed_if_now_od = remaining_work + restart_overhead
        slack_after_od = remaining_wall - time_needed_if_now_od

        if slack_after_od <= self._safety_margin:
            self._lock_on_od = True

        if self._lock_on_od:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        slack_if_idle_then_od = remaining_wall - gap - time_needed_if_now_od

        if slack_if_idle_then_od > self._safety_margin:
            return ClusterType.NONE

        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
