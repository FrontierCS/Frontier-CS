from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_safe_spot_v1"

    def __init__(self, args=None):
        super().__init__(args)
        self.committed_on_demand = False
        self._initialized = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _ensure_initialized(self):
        if not self._initialized:
            self.committed_on_demand = False
            self._initialized = True

    def _estimate_remaining_work(self) -> float:
        env = self.env
        gap = getattr(env, "gap_seconds", 1.0)
        if getattr(self, "task_done_time", None) is None:
            done_segments = 0
        else:
            try:
                done_segments = len(self.task_done_time)
            except TypeError:
                try:
                    done_segments = int(self.task_done_time)
                except Exception:
                    done_segments = 0
        progress = done_segments * gap
        remaining = self.task_duration - progress
        if remaining < 0.0:
            remaining = 0.0
        return remaining

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_initialized()

        env = self.env
        gap = getattr(env, "gap_seconds", 1.0)
        now = getattr(env, "elapsed_seconds", 0.0)

        remaining = self._estimate_remaining_work()

        if remaining <= 0.0:
            self.committed_on_demand = True
            return ClusterType.NONE

        deadline = self.deadline
        time_left = deadline - now
        if time_left <= 0.0:
            self.committed_on_demand = True
            return ClusterType.ON_DEMAND

        restart_overhead = getattr(self, "restart_overhead", 0.0)

        if self.committed_on_demand:
            return ClusterType.ON_DEMAND

        safety_margin = 0.5 * gap
        safety_term = restart_overhead + gap + safety_margin

        if time_left < remaining + safety_term:
            self.committed_on_demand = True
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
