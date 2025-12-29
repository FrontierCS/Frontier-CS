from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args=None):
        super().__init__(args)
        self._commit_to_od = False
        self._safety_margin = None
        self._last_env_id = None

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _compute_safety_margin(self):
        try:
            slack = float(self.deadline) - float(self.task_duration)
        except Exception:
            slack = 0.0
        if slack <= 0.0:
            return 0.0
        # Use up to 20% of slack as a safety margin, capped at 1 hour.
        margin = slack * 0.2
        one_hour = 3600.0
        if margin > one_hour:
            margin = one_hour
        return margin

    def _estimate_work_done_lower_bound(self) -> float:
        td = getattr(self, "task_done_time", None)
        if td is None:
            return 0.0
        try:
            if len(td) == 0:
                return 0.0
        except TypeError:
            # td is not sized; fall back to iteration
            pass
        try:
            # Use max as a lower bound on total work done.
            return float(max(td))
        except Exception:
            # Robust fallback in case of mixed/invalid entries.
            max_val = 0.0
            try:
                for v in td:
                    try:
                        fv = float(v)
                        if fv > max_val:
                            max_val = fv
                    except Exception:
                        continue
            except Exception:
                pass
            return max_val

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Detect new environment / episode and reset internal state.
        env_id = id(self.env)
        if env_id != self._last_env_id:
            self._last_env_id = env_id
            self._commit_to_od = False
            self._safety_margin = None

        if self._safety_margin is None:
            self._safety_margin = self._compute_safety_margin()

        work_done_lb = self._estimate_work_done_lower_bound()
        try:
            task_duration = float(self.task_duration)
        except Exception:
            task_duration = 0.0

        remaining = task_duration - work_done_lb
        if remaining <= 0.0:
            return ClusterType.NONE

        try:
            elapsed = float(self.env.elapsed_seconds)
        except Exception:
            elapsed = 0.0
        try:
            gap = float(self.env.gap_seconds)
        except Exception:
            gap = 0.0
        try:
            restart_overhead = float(self.restart_overhead)
        except Exception:
            restart_overhead = 0.0
        try:
            deadline = float(self.deadline)
        except Exception:
            deadline = elapsed + gap + restart_overhead + remaining + self._safety_margin + 1.0

        margin = self._safety_margin or 0.0

        if (not self._commit_to_od and
                elapsed + gap + restart_overhead + remaining + margin > deadline):
            self._commit_to_od = True

        if self._commit_to_od:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)