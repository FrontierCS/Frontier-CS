from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_safewait_v1"

    def __init__(self, args=None):
        super().__init__(args)
        self._eps = 1e-9
        self._overhead_mult = 1.0  # Safety multiplier on restart_overhead

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _remaining_work(self) -> float:
        if not self.task_done_time:
            return self.task_duration
        done = sum(self.task_done_time)
        remaining = self.task_duration - done
        if remaining < 0.0:
            return 0.0
        return remaining

    def _time_to_deadline(self) -> float:
        return max(self.deadline - self.env.elapsed_seconds, 0.0)

    def _safe_slack(self) -> float:
        # Slack = time to deadline - remaining work (seconds)
        # Positive slack means we have extra time beyond the bare minimum.
        return self._time_to_deadline() - self._remaining_work()

    def _must_use_on_demand_now(self) -> bool:
        # We must ensure that, even if a preemption happens right before we commit
        # to on-demand, we can still finish. Budget exactly one restart_overhead.
        required_slack = self.restart_overhead * self._overhead_mult
        return self._safe_slack() < required_slack - self._eps

    def _can_wait_one_step(self) -> bool:
        # Decide if we can idle for one step and still remain safe
        step = self.env.gap_seconds
        ttd_after_wait = max(self._time_to_deadline() - step, 0.0)
        required = self._remaining_work() + self.restart_overhead * self._overhead_mult
        return ttd_after_wait >= required - self._eps

    def _should_use_spot(self) -> bool:
        # Use spot when available if we still maintain enough slack to tolerate one restart overhead.
        required = self._remaining_work() + self.restart_overhead * self._overhead_mult
        return self._time_to_deadline() >= required - self._eps

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        remaining_work = self._remaining_work()
        if remaining_work <= 0.0:
            return ClusterType.NONE

        if has_spot:
            if self._should_use_spot():
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND
        else:
            if self._can_wait_one_step():
                return ClusterType.NONE
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
