from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_greedy_fallback"

    def solve(self, spec_path: str) -> "Solution":
        # Optional initialization
        self._safety_margin_seconds = 600.0  # 10 minutes default buffer
        self._on_demand_only = False
        self._initialized_internal = False
        self._spec_path = spec_path
        return self

    def _initialize_if_needed(self):
        if getattr(self, "_initialized_internal", False):
            return
        base_margin = getattr(self, "_safety_margin_seconds", 600.0)
        self._on_demand_only = getattr(self, "_on_demand_only", False)

        gap = 0.0
        overhead = 0.0
        try:
            gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        except Exception:
            gap = 0.0
        try:
            overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        except Exception:
            overhead = 0.0

        adaptive_margin = gap + 2.0 * overhead
        self._safety_margin_seconds = max(base_margin, adaptive_margin)
        self._initialized_internal = True

    def _compute_work_done(self) -> float:
        segments = getattr(self, "task_done_time", None)
        if not segments:
            return 0.0

        total_seg = 0.0
        last_scalar = None

        if isinstance(segments, (list, tuple)):
            for seg in segments:
                if isinstance(seg, (list, tuple)) and len(seg) >= 2:
                    try:
                        start = float(seg[0])
                        end = float(seg[1])
                        if end > start:
                            total_seg += end - start
                    except Exception:
                        continue
                elif isinstance(seg, (int, float)):
                    val = float(seg)
                    if last_scalar is None or val > last_scalar:
                        last_scalar = val
        else:
            if isinstance(segments, (int, float)):
                return float(segments)
            return 0.0

        if total_seg > 0.0:
            return total_seg
        if last_scalar is not None:
            return last_scalar
        return 0.0

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._initialize_if_needed()

        if getattr(self, "_on_demand_only", False):
            return ClusterType.ON_DEMAND

        try:
            task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        except Exception:
            task_duration = 0.0
        try:
            deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        except Exception:
            deadline = 0.0

        env = getattr(self, "env", None)
        elapsed = 0.0
        gap = 0.0
        if env is not None:
            try:
                elapsed = float(getattr(env, "elapsed_seconds", 0.0) or 0.0)
            except Exception:
                elapsed = 0.0
            try:
                gap = float(getattr(env, "gap_seconds", 0.0) or 0.0)
            except Exception:
                gap = 0.0

        try:
            overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        except Exception:
            overhead = 0.0

        margin = float(getattr(self, "_safety_margin_seconds", 600.0) or 600.0)

        if task_duration <= 0.0 or deadline <= 0.0:
            if has_spot:
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND

        work_done = self._compute_work_done()
        remaining_work = task_duration - work_done
        if remaining_work <= 0.0:
            self._on_demand_only = True
            return ClusterType.NONE

        slack = deadline - elapsed - remaining_work

        if slack <= 0.0:
            self._on_demand_only = True
            return ClusterType.ON_DEMAND

        worst_case_next_time = elapsed + gap + overhead
        if worst_case_next_time + remaining_work <= deadline - margin:
            if has_spot:
                return ClusterType.SPOT
            return ClusterType.NONE

        self._on_demand_only = True
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
