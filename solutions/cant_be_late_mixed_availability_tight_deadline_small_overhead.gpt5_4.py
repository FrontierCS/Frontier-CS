from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_threshold"

    def __init__(self, args=None):
        self.args = args
        self._commit_to_od = False
        self.extra_buffer_seconds = 0.0
        if args is not None and hasattr(args, "extra_buffer_seconds") and args.extra_buffer_seconds is not None:
            try:
                self.extra_buffer_seconds = float(args.extra_buffer_seconds)
            except Exception:
                self.extra_buffer_seconds = 0.0

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _remaining_work(self) -> float:
        try:
            done = sum(self.task_done_time) if hasattr(self, "task_done_time") and self.task_done_time is not None else 0.0
        except Exception:
            done = 0.0
        total = float(getattr(self, "task_duration", 0.0) or 0.0)
        remaining = max(0.0, total - float(done))
        return remaining

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If already committed to on-demand, stick with it to avoid extra overhead/risk
        if self._commit_to_od or last_cluster_type == ClusterType.ON_DEMAND:
            self._commit_to_od = True
            # If task is already done, don't keep paying
            if self._remaining_work() <= 1e-9:
                return ClusterType.NONE
            return ClusterType.ON_DEMAND

        # Compute remaining work and basic parameters
        remain = self._remaining_work()
        if remain <= 1e-9:
            return ClusterType.NONE

        e = float(self.env.elapsed_seconds)
        dt = float(self.env.gap_seconds)
        deadline = float(self.deadline)
        oh = float(self.restart_overhead) + float(self.extra_buffer_seconds)

        # If we can finish on spot within this step safely, do it (cheaper)
        if has_spot:
            if last_cluster_type == ClusterType.SPOT:
                step_work_spot = dt
            else:
                step_work_spot = max(0.0, dt - oh)
            if remain <= step_work_spot + 1e-12:
                return ClusterType.SPOT

        # Latest time to start OD (including a single restart overhead) to finish by deadline
        latest_start_od = deadline - (remain + oh)

        # If postponing OD by one more step risks missing the deadline, commit to OD now
        if e + dt > latest_start_od + 1e-12:
            self._commit_to_od = True
            return ClusterType.ON_DEMAND

        # Otherwise, it's safe to wait: prefer spot if available; else pause to save cost
        if has_spot:
            return ClusterType.SPOT
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        parser.add_argument("--extra_buffer_seconds", type=float, default=0.0)
        args, _ = parser.parse_known_args()
        return cls(args)
