from typing import Any, Sequence
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_v1"

    def __init__(self, args=None):
        # Safety margin parameters
        self.safety_overhead_mult = getattr(args, "safety_overhead_mult", 2.5)
        self.safety_gap_mult = getattr(args, "safety_gap_mult", 4.0)
        self.min_safety_minutes = getattr(args, "min_safety_minutes", 30.0)
        self.min_safety_seconds = self.min_safety_minutes * 60.0

        # Internal state
        self._committed_to_od = False
        self._last_done_idx = 0
        self._done_sum = 0.0

    def solve(self, spec_path: str) -> "Solution":
        # No pre-processing needed; keep the interface
        return self

    def _safe_margin_seconds(self, gap_s: float) -> float:
        oh = float(getattr(self, "restart_overhead", 0.0))
        return max(self.min_safety_seconds, self.safety_overhead_mult * oh, self.safety_gap_mult * gap_s)

    def _elem_duration(self, x: Any) -> float:
        # Robustly extract a duration from diverse possible formats
        try:
            if isinstance(x, (int, float)):
                return float(x)
            if isinstance(x, dict):
                if "duration" in x:
                    return float(x.get("duration", 0.0))
                if "end" in x and "start" in x:
                    return max(0.0, float(x["end"]) - float(x["start"]))
                return 0.0
            if isinstance(x, Sequence):
                if len(x) == 2 and all(isinstance(v, (int, float)) for v in x):
                    return max(0.0, float(x[1]) - float(x[0]))
                # If it's a sequence of numbers, sum them
                if all(isinstance(v, (int, float)) for v in x):
                    return float(sum(x))
            return 0.0
        except Exception:
            return 0.0

    def _progress_done_seconds(self) -> float:
        lst = getattr(self, "task_done_time", None)
        if lst is None:
            return self._done_sum
        try:
            n = len(lst)
        except Exception:
            # Fallback: try to interpret it directly
            try:
                return float(lst)
            except Exception:
                return self._done_sum

        if n < self._last_done_idx:
            # List got reset; recompute
            self._done_sum = 0.0
            self._last_done_idx = 0

        # Accumulate new items
        for i in range(self._last_done_idx, n):
            self._done_sum += self._elem_duration(lst[i])
        self._last_done_idx = n
        return self._done_sum

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If we've already started OD, stick to it (avoid thrash)
        if last_cluster_type == ClusterType.ON_DEMAND:
            self._committed_to_od = True

        # Compute remaining work
        done_sec = self._progress_done_seconds()
        total_needed = float(getattr(self, "task_duration", 0.0))
        remaining = max(0.0, total_needed - done_sec)
        if remaining <= 0.0:
            return ClusterType.NONE

        # Environment parameters
        t = float(getattr(self.env, "elapsed_seconds", 0.0))
        gap = float(getattr(self.env, "gap_seconds", 60.0))
        deadline = float(getattr(self, "deadline", t + remaining))
        restart_overhead = float(getattr(self, "restart_overhead", 0.0))

        # Safety margin to preserve before committing to OD
        safety_margin = self._safe_margin_seconds(gap)

        # Overhead if we switch to OD from our current mode in the future
        od_overhead_future = 0.0 if self._committed_to_od or last_cluster_type == ClusterType.ON_DEMAND else restart_overhead

        # Allowed waiting time while still being able to finish by switching to OD (including one restart overhead)
        allowed_wait = (deadline - t) - (od_overhead_future + remaining)

        # Commit to OD if we are inside safety margin
        if not self._committed_to_od and allowed_wait <= safety_margin:
            self._committed_to_od = True

        # If committed, always choose OD
        if self._committed_to_od:
            return ClusterType.ON_DEMAND

        # Not committed: prefer SPOT when available and we have slack
        if has_spot:
            # Use SPOT as long as we maintain the safety margin
            return ClusterType.SPOT

        # Spot unavailable:
        # If we can afford to wait one more step (keeping margin), do NONE; else commit to OD
        if allowed_wait >= (gap + safety_margin) and last_cluster_type != ClusterType.ON_DEMAND:
            return ClusterType.NONE

        # Need to ensure completion: use OD and commit
        self._committed_to_od = True
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        parser.add_argument("--safety_overhead_mult", type=float, default=2.5)
        parser.add_argument("--safety_gap_mult", type=float, default=4.0)
        parser.add_argument("--min_safety_minutes", type=float, default=30.0)
        args, _ = parser.parse_known_args()
        return cls(args)