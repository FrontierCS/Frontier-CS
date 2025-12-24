from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_heuristic_v1"

    def __init__(self, args):
        super().__init__(args)
        self._margin_seconds = None
        self._cached_done_len = 0
        self._cached_done_sum = 0.0

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _compute_margin(self) -> float:
        if self._margin_seconds is not None:
            return self._margin_seconds

        # Fallbacks in case attributes are not yet set (defensive)
        restart_overhead = float(getattr(self, "restart_overhead", 0.0))
        gap_seconds = float(getattr(self.env, "gap_seconds", 0.0))

        # Margin ensures we never "waste" more than one gap interval of slack
        # beyond the restart overhead before committing to on-demand.
        self._margin_seconds = max(0.0, restart_overhead + gap_seconds)
        return self._margin_seconds

    def _remaining_work_seconds(self) -> float:
        task_duration = float(getattr(self, "task_duration", 0.0))
        done_list = getattr(self, "task_done_time", None)

        if not done_list:
            done_sum = 0.0
        else:
            cur_len = len(done_list)
            if cur_len != self._cached_done_len:
                # Recompute sum only when new segments are added
                done_sum = float(sum(done_list))
                self._cached_done_len = cur_len
                self._cached_done_sum = done_sum
            else:
                done_sum = self._cached_done_sum

        remaining = task_duration - done_sum
        if remaining < 0.0:
            return 0.0
        return remaining

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        margin = self._compute_margin()
        remaining = self._remaining_work_seconds()

        # If job is already done (defensive), do nothing.
        if remaining <= 0.0:
            return ClusterType.NONE

        now = float(getattr(self.env, "elapsed_seconds", 0.0))
        deadline = float(getattr(self, "deadline", 0.0))

        slack = deadline - now - remaining

        # If slack is small, commit to on-demand to guarantee completion.
        if slack <= margin:
            return ClusterType.ON_DEMAND

        # Otherwise, use spot when available; pause when not, to save cost.
        if has_spot:
            return ClusterType.SPOT
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
