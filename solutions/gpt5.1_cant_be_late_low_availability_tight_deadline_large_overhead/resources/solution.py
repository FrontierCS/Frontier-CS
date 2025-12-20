from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_heuristic_v1"

    def __init__(self, args=None):
        super().__init__(args)
        self.args = args
        self._initialized = False
        self._initial_slack = 0.0
        self._safety_buffer = 0.0
        self._force_on_demand = False
        self._cached_done_segments_count = 0
        self._cached_done_work = 0.0

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _initialize_if_needed(self):
        if self._initialized:
            return
        self._initialized = True
        try:
            task_duration = float(self.task_duration)
        except Exception:
            task_duration = 0.0
        try:
            deadline = float(self.deadline)
        except Exception:
            deadline = task_duration
        slack = max(0.0, deadline - task_duration)
        self._initial_slack = slack
        gap = getattr(self.env, "gap_seconds", 0.0) or 0.0
        restart_overhead = getattr(self, "restart_overhead", 0.0) or 0.0
        base_buffer = restart_overhead + gap
        frac_buffer = 0.1 * slack
        self._safety_buffer = max(base_buffer, frac_buffer)

    def _segment_duration(self, seg) -> float:
        if seg is None:
            return 0.0
        if isinstance(seg, (int, float)):
            v = float(seg)
            return v if v > 0.0 else 0.0
        if isinstance(seg, dict):
            if "duration" in seg:
                try:
                    v = float(seg["duration"])
                    return v if v > 0.0 else 0.0
                except Exception:
                    pass
            if "start" in seg and "end" in seg:
                try:
                    v = float(seg["end"]) - float(seg["start"])
                    return v if v > 0.0 else 0.0
                except Exception:
                    pass
        if isinstance(seg, (list, tuple)):
            if (
                len(seg) >= 2
                and isinstance(seg[0], (int, float))
                and isinstance(seg[1], (int, float))
            ):
                v = float(seg[1]) - float(seg[0])
                return v if v > 0.0 else 0.0
            if len(seg) == 1 and isinstance(seg[0], (int, float)):
                v = float(seg[0])
                return v if v > 0.0 else 0.0
        if hasattr(seg, "duration"):
            try:
                v = float(seg.duration)
                if v > 0.0:
                    return v
            except Exception:
                pass
        if hasattr(seg, "start") and hasattr(seg, "end"):
            try:
                v = float(seg.end) - float(seg.start)
                return v if v > 0.0 else 0.0
            except Exception:
                pass
        return 0.0

    def _compute_done_work(self) -> float:
        segments = getattr(self, "task_done_time", None)
        if not segments:
            return 0.0
        try:
            seg_list = list(segments)
        except TypeError:
            return 0.0
        n = len(seg_list)
        if n < self._cached_done_segments_count:
            self._cached_done_segments_count = 0
            self._cached_done_work = 0.0
        for i in range(self._cached_done_segments_count, n):
            self._cached_done_work += self._segment_duration(seg_list[i])
        self._cached_done_segments_count = n
        try:
            task_duration = float(self.task_duration)
        except Exception:
            task_duration = None
        if task_duration is not None and task_duration > 0.0:
            if self._cached_done_work > task_duration:
                self._cached_done_work = task_duration
        return self._cached_done_work

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._initialize_if_needed()
        try:
            task_duration = float(self.task_duration)
        except Exception:
            task_duration = 0.0
        done = self._compute_done_work()
        remaining_work = max(0.0, task_duration - done)
        try:
            now = float(self.env.elapsed_seconds)
        except Exception:
            now = 0.0
        try:
            deadline = float(self.deadline)
        except Exception:
            deadline = now
        time_left = deadline - now
        if remaining_work <= 0.0:
            return ClusterType.NONE
        if time_left <= 0.0:
            return ClusterType.ON_DEMAND
        restart_overhead = getattr(self, "restart_overhead", 0.0) or 0.0
        gap = getattr(self.env, "gap_seconds", 0.0) or 0.0
        safety_buffer = self._safety_buffer if self._safety_buffer is not None else 0.0
        allowed_waste = time_left - remaining_work - restart_overhead - safety_buffer
        if allowed_waste <= 0.0:
            self._force_on_demand = True
        if self._force_on_demand:
            return ClusterType.ON_DEMAND
        if has_spot:
            return ClusterType.SPOT
        if allowed_waste >= gap:
            return ClusterType.NONE
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
