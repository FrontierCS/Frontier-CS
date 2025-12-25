from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "deadline_guard_v3"

    def __init__(self, args=None):
        super().__init__(args)
        self._commit_to_od = False
        self._od_commit_time = None

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _remaining_work(self) -> float:
        done = 0.0
        if getattr(self, "task_done_time", None):
            try:
                done = float(sum(self.task_done_time))
            except Exception:
                done = 0.0
        rem = getattr(self, "task_duration", 0.0) - done
        return rem if rem > 0.0 else 0.0

    def _time_left(self) -> float:
        try:
            return max(0.0, self.deadline - self.env.elapsed_seconds)
        except Exception:
            return 0.0

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If we've already committed to on-demand, keep using it.
        if self._commit_to_od:
            return ClusterType.ON_DEMAND

        rem_work = self._remaining_work()
        if rem_work <= 0.0:
            return ClusterType.NONE

        dt = getattr(self.env, "gap_seconds", 0.0) or 0.0
        # Safety margin to account for step discretization and any tiny timing drift.
        fudge = 1.5 * dt + 1e-9

        time_left = self._time_left()
        r_overhead = getattr(self, "restart_overhead", 0.0) or 0.0

        # If we must ensure completion with on-demand including restart overhead and discretization.
        must_commit_now = time_left <= (rem_work + r_overhead + fudge)

        if must_commit_now:
            self._commit_to_od = True
            self._od_commit_time = getattr(self.env, "elapsed_seconds", None)
            return ClusterType.ON_DEMAND

        # Prefer SPOT when available, otherwise pause if we can still safely wait; else commit to OD.
        if has_spot:
            return ClusterType.SPOT

        # Spot not available: can we afford to wait for one more step?
        can_wait_one_step = (time_left - dt) > (rem_work + r_overhead + fudge)
        if can_wait_one_step:
            return ClusterType.NONE

        # Can't wait further; commit to on-demand to guarantee finish.
        self._commit_to_od = True
        self._od_commit_time = getattr(self.env, "elapsed_seconds", None)
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)