import math
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_heuristic_v1"

    def __init__(self, *args, **kwargs):
        try:
            super().__init__(*args, **kwargs)
        except TypeError:
            try:
                super().__init__()
            except TypeError:
                pass
        self.force_on_demand = False
        self._thresholds_initialized = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)

    def _initialize_thresholds(self):
        if self._thresholds_initialized:
            return

        gap = getattr(self.env, "gap_seconds", 60.0) or 60.0
        restart_ovh = getattr(self, "restart_overhead", getattr(self.env, "restart_overhead", 0.0)) or 0.0
        deadline = getattr(self, "deadline", getattr(self.env, "deadline", None))
        task_duration = getattr(self, "task_duration", None)

        if deadline is None or task_duration is None:
            initial_slack = 6 * 3600.0  # fallback: 6 hours
        else:
            initial_slack = max(deadline - task_duration, 0.0)

        margin_min = restart_ovh + 2.0 * gap
        margin = max(margin_min, 0.5 * gap)

        wait_slack = max(0.25 * initial_slack, 2.0 * 3600.0)
        wait_slack = max(wait_slack, margin + 3.0 * gap)

        self._gap = gap
        self._restart_overhead = restart_ovh
        self._salvage_margin = margin
        self._wait_for_spot_slack = wait_slack
        self._thresholds_initialized = True

    def _compute_done_time(self):
        segments = getattr(self, "task_done_time", None)
        if not segments:
            return 0.0
        total = 0.0
        for seg in segments:
            if seg is None:
                continue
            if isinstance(seg, (int, float)):
                total += float(seg)
                continue
            if isinstance(seg, (list, tuple)):
                if len(seg) >= 2 and isinstance(seg[0], (int, float)) and isinstance(seg[1], (int, float)):
                    total += float(seg[1] - seg[0])
                    continue
            if isinstance(seg, dict):
                if "duration" in seg and isinstance(seg["duration"], (int, float)):
                    total += float(seg["duration"])
                    continue
                if (
                    "start" in seg
                    and "end" in seg
                    and isinstance(seg["start"], (int, float))
                    and isinstance(seg["end"], (int, float))
                ):
                    total += float(seg["end"] - seg["start"])
                    continue
            dur = getattr(seg, "duration", None)
            if isinstance(dur, (int, float)):
                total += float(dur)
                continue
            s = getattr(seg, "start", None)
            e = getattr(seg, "end", None)
            if isinstance(s, (int, float)) and isinstance(e, (int, float)):
                total += float(e - s)
                continue
        return max(total, 0.0)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not self._thresholds_initialized:
            self._initialize_thresholds()

        elapsed = getattr(self.env, "elapsed_seconds", 0.0) or 0.0
        deadline = getattr(self, "deadline", getattr(self.env, "deadline", None))
        if deadline is None:
            return ClusterType.SPOT if has_spot else ClusterType.ON_DEMAND

        done_time = self._compute_done_time()
        task_duration = getattr(self, "task_duration", None)
        if task_duration is None:
            return ClusterType.SPOT if has_spot else ClusterType.ON_DEMAND

        remaining = max(task_duration - done_time, 0.0)
        time_left = max(deadline - elapsed, 0.0)
        slack = time_left - remaining

        if remaining <= 0.0:
            return ClusterType.NONE

        if getattr(self, "force_on_demand", False):
            return ClusterType.ON_DEMAND

        if slack <= self._salvage_margin:
            self.force_on_demand = True
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        if slack > self._wait_for_spot_slack:
            return ClusterType.NONE

        return ClusterType.ON_DEMAND
