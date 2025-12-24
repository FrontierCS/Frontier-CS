from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cbl_threshold_v1"

    def __init__(self, args=None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except Exception:
                pass
        # Configurable parameters (in hours)
        self.commit_buffer_hours = getattr(args, "commit_buffer_hours", 2.0)
        self.dynamic_buffer_hour_max = getattr(args, "dynamic_buffer_hour_max", 1.0)
        self.committed_od = False

    def solve(self, spec_path: str) -> "Solution":
        # Reset any run-specific state if needed
        self.committed_od = False
        return self

    def _remaining_work_seconds(self) -> float:
        try:
            done = float(sum(self.task_done_time)) if self.task_done_time else 0.0
        except Exception:
            done = 0.0
        rem = float(self.task_duration) - done
        return rem if rem > 0.0 else 0.0

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If already committed to OD, stay on OD
        remaining = self._remaining_work_seconds()
        if remaining <= 0.0:
            return ClusterType.NONE

        # Time left to deadline
        try:
            t_left = float(self.deadline) - float(self.env.elapsed_seconds)
        except Exception:
            t_left = float(self.deadline)

        if t_left <= 0.0:
            # Out of time; best effort: use OD
            self.committed_od = True
            return ClusterType.ON_DEMAND

        # Dynamic buffer based on required pace
        r_req = remaining / max(t_left, 1e-9)
        # Add up to dynamic_buffer_hour_max hours when r_req is high
        # Scale from r_req >= 0.7 to >= 0.9
        scale = 0.0
        if r_req > 0.7:
            scale = min(1.0, max(0.0, (r_req - 0.7) / 0.2))
        dynamic_buf_s = self.dynamic_buffer_hour_max * 3600.0 * scale

        commit_buffer_s = max(self.commit_buffer_hours * 3600.0, 6.0 * float(self.restart_overhead))
        total_buffer_s = commit_buffer_s + dynamic_buf_s

        if self.committed_od:
            return ClusterType.ON_DEMAND

        # Overhead if switching to OD now
        od_switch_overhead = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else float(self.restart_overhead)

        # Commit condition: ensure we switch to OD early enough
        if t_left <= remaining + od_switch_overhead + total_buffer_s:
            self.committed_od = True
            return ClusterType.ON_DEMAND

        # Prefer SPOT when available
        if has_spot:
            return ClusterType.SPOT

        # Spot unavailable: wait if safe, else commit to OD
        if t_left <= remaining + od_switch_overhead + total_buffer_s:
            self.committed_od = True
            return ClusterType.ON_DEMAND

        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        parser.add_argument("--commit-buffer-hours", type=float, default=2.0)
        parser.add_argument("--dynamic-buffer-hour-max", type=float, default=1.0)
        args, _ = parser.parse_known_args()
        return cls(args)
