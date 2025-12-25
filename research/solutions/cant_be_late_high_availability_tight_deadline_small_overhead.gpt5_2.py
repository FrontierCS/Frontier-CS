from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "deadline_guard_threshold_v1"

    def __init__(self, args=None):
        super().__init__(args)
        self.force_od = False
        self.od_commit_time = None

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _sum_done(self):
        total = 0.0
        if not getattr(self, "task_done_time", None):
            return 0.0
        try:
            return float(sum(self.task_done_time))
        except Exception:
            for seg in self.task_done_time:
                try:
                    total += float(seg)
                except Exception:
                    try:
                        if isinstance(seg, (list, tuple)) and len(seg) >= 2:
                            total += float(seg[1]) - float(seg[0])
                    except Exception:
                        continue
            return total

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If we've already committed to on-demand, stick with it to avoid extra restarts.
        if self.force_od:
            return ClusterType.ON_DEMAND

        # Basic time quantities
        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0))
        gap = float(getattr(self.env, "gap_seconds", 60.0))
        deadline = float(getattr(self, "deadline", elapsed + 1e9))
        restart_overhead = float(getattr(self, "restart_overhead", 0.0))
        task_duration = float(getattr(self, "task_duration", 0.0))

        done = self._sum_done()
        remaining = max(0.0, task_duration - done)
        if remaining <= 0.0:
            return ClusterType.NONE

        time_left = max(0.0, deadline - elapsed)

        # Safety buffer to account for discretization and small timing errors.
        safety = max(2.0 * gap, 0.75 * restart_overhead)

        # Overhead if we switch to OD now (0 if already on OD).
        od_overhead_now = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else restart_overhead
        od_time_needed_now = remaining + od_overhead_now

        # If we must switch to OD to guarantee completion, do it now.
        if time_left <= od_time_needed_now + safety:
            self.force_od = True
            self.od_commit_time = elapsed
            return ClusterType.ON_DEMAND

        # Prefer SPOT when available and safe.
        if has_spot:
            return ClusterType.SPOT

        # SPOT not available. Decide to wait or switch to OD.
        # If waiting one more step still leaves enough time for OD (including overhead) with buffer, wait.
        if time_left - gap > od_time_needed_now + safety:
            return ClusterType.NONE

        # Otherwise, commit to OD to ensure deadline.
        self.force_od = True
        self.od_commit_time = elapsed
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)