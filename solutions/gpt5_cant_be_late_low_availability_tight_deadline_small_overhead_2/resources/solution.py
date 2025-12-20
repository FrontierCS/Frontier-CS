from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "deadline_threshold_lock"

    def solve(self, spec_path: str) -> "Solution":
        # Initialization
        self._locked_to_od = False
        self._last_done_len = 0
        self._done_sum_cache = 0.0
        # Optional config via args
        args = getattr(self, "args", None)
        if args is not None and hasattr(args, "od_margin_factor"):
            self._od_margin_factor = float(args.od_margin_factor)
        else:
            self._od_margin_factor = 1.0
        return self

    def _remaining_work_seconds(self) -> float:
        # Incremental sum to avoid O(n) per step
        lst = self.task_done_time
        current_len = len(lst)
        if current_len > self._last_done_len:
            # Sum only new segments
            inc = 0.0
            for i in range(self._last_done_len, current_len):
                inc += lst[i]
            self._done_sum_cache += inc
            self._last_done_len = current_len
        # Remaining work cannot be negative
        remaining = self.task_duration - self._done_sum_cache
        return remaining if remaining > 0.0 else 0.0

    def _should_lock_to_od(self) -> bool:
        remaining = self._remaining_work_seconds()
        if remaining <= 0.0:
            return False
        time_left = self.deadline - self.env.elapsed_seconds
        if time_left <= 0.0:
            # Already missed, but ensure OD (defensive)
            return True
        overhead = 0.0 if self.env.cluster_type == ClusterType.ON_DEMAND else self.restart_overhead
        # Margin scaled by the step; keeps safety against discretization effects
        margin = self._od_margin_factor * self.env.gap_seconds
        # If we do not start OD now, we risk missing deadline
        return time_left <= (remaining + overhead + margin)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If already done, no need to run further
        if self._remaining_work_seconds() <= 0.0:
            return ClusterType.NONE

        # Decide whether we must lock to on-demand to meet the deadline
        if not self._locked_to_od and self._should_lock_to_od():
            self._locked_to_od = True

        if self._locked_to_od:
            return ClusterType.ON_DEMAND

        # Not locked yet: prefer spot when available, otherwise wait
        if has_spot:
            return ClusterType.SPOT
        else:
            # Wait for spot to return until it's time-critical
            # The lock condition will trigger when necessary
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        parser.add_argument("--od_margin_factor", type=float, default=1.0)
        args, _ = parser.parse_known_args()
        return cls(args)
