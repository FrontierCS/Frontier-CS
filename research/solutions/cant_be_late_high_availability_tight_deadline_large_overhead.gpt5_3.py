from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_threshold_v2"

    def solve(self, spec_path: str) -> "Solution":
        self._last_seen_elapsed = None
        self._od_locked = False
        return self

    def _reset_run_state_if_needed(self):
        curr_elapsed = getattr(self.env, "elapsed_seconds", 0.0)
        if self._last_seen_elapsed is None or curr_elapsed < self._last_seen_elapsed:
            self._od_locked = False
        self._last_seen_elapsed = curr_elapsed

    def _guard_time(self) -> float:
        gap = getattr(self.env, "gap_seconds", 0.0) or 0.0
        restart = getattr(self, "restart_overhead", 0.0) or 0.0
        # Guard at least one step, but also provide a small fixed buffer
        return max(gap, restart * 0.25)

    def _remaining_work(self) -> float:
        done = 0.0
        if getattr(self, "task_done_time", None):
            try:
                done = sum(self.task_done_time)
            except Exception:
                done = 0.0
        total = getattr(self, "task_duration", 0.0) or 0.0
        remain = total - done
        return remain if remain > 0.0 else 0.0

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._reset_run_state_if_needed()

        # If already running on OD, lock to OD until completion to avoid thrashing.
        if last_cluster_type == ClusterType.ON_DEMAND:
            self._od_locked = True

        remaining = self._remaining_work()
        if remaining <= 0.0:
            return ClusterType.NONE

        t_left = (getattr(self, "deadline", 0.0) or 0.0) - (getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        guard = self._guard_time()
        # If not locked yet, evaluate whether we must switch to OD now to guarantee finishing
        if not self._od_locked:
            # Need to budget one restart overhead when initiating OD.
            need_time_if_start_od_now = remaining + (self.restart_overhead or 0.0)
            if t_left <= need_time_if_start_od_now + guard:
                self._od_locked = True

        if self._od_locked:
            return ClusterType.ON_DEMAND

        # Not locked to OD: prefer Spot when available; otherwise idle if safe.
        if has_spot:
            return ClusterType.SPOT

        # Spot unavailable: check if we can afford to wait; otherwise start OD.
        need_time_if_start_od_now = remaining + (self.restart_overhead or 0.0)
        if t_left <= need_time_if_start_od_now + guard:
            return ClusterType.ON_DEMAND
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)