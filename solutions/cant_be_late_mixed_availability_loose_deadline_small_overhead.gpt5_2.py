from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_threshold_v3"

    def __init__(self, args=None):
        super().__init__(args)
        # Safety parameters
        self.guard_mult = getattr(args, "guard_mult", 2.0) if args is not None else 2.0
        self.min_guard_seconds = getattr(args, "min_guard_seconds", 300.0) if args is not None else 300.0
        self.extra_guard_overhead_frac = getattr(args, "extra_guard_overhead_frac", 0.5) if args is not None else 0.5

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _done_seconds(self) -> float:
        t = getattr(self, "task_done_time", 0.0)
        try:
            if isinstance(t, (int, float)):
                return float(t)
            return float(sum(t))
        except Exception:
            try:
                return float(sum(list(t)))
            except Exception:
                return 0.0

    def _compute_guard(self) -> float:
        dt = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        base = max(self.min_guard_seconds, self.guard_mult * dt)
        overhead_cushion = self.extra_guard_overhead_frac * overhead
        return base + overhead_cushion

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Task completed
        done = self._done_seconds()
        total = float(getattr(self, "task_duration", 0.0) or 0.0)
        remaining = max(0.0, total - done)
        if remaining <= 0.0:
            return ClusterType.NONE

        now = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        time_left = max(0.0, deadline - now)

        guard = self._compute_guard()
        restart_overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        switch_overhead_to_od = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else restart_overhead

        # If we are at or inside the latest safe time to start OD, choose OD to guarantee completion.
        if time_left <= remaining + switch_overhead_to_od + guard:
            return ClusterType.ON_DEMAND

        # Otherwise, prefer Spot if available; else wait to save cost.
        if has_spot:
            return ClusterType.SPOT

        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        parser.add_argument("--guard_mult", type=float, default=2.0)
        parser.add_argument("--min_guard_seconds", type=float, default=300.0)
        parser.add_argument("--extra_guard_overhead_frac", type=float, default=0.5)
        args, _ = parser.parse_known_args()
        return cls(args)
