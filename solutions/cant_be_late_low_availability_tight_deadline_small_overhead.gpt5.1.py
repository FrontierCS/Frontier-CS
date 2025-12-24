import math
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        # Optional: store spec path or parse it if needed
        self.force_on_demand = False
        self._margin_seconds = None
        return self

    def _compute_done_work(self) -> float:
        lst = getattr(self, "task_done_time", None)
        if not lst:
            return 0.0

        try:
            first = lst[0]
        except Exception:
            return 0.0

        # Case 1: list of segments, e.g., (start, end) or (start, end, ...)
        if isinstance(first, (list, tuple)):
            if len(first) >= 2 and isinstance(first[0], (int, float)) and isinstance(first[1], (int, float)):
                total = 0.0
                valid_segments = 0
                for seg in lst:
                    if (
                        isinstance(seg, (list, tuple))
                        and len(seg) >= 2
                        and isinstance(seg[0], (int, float))
                        and isinstance(seg[1], (int, float))
                        and seg[1] >= seg[0]
                    ):
                        total += seg[1] - seg[0]
                        valid_segments += 1
                if valid_segments > 0:
                    return float(total)

            # Fallback for tuple/list where second element might be cumulative done
            last = lst[-1]
            if isinstance(last, (list, tuple)) and len(last) >= 2 and isinstance(last[1], (int, float)):
                return float(last[1])

        # Case 2: list of numeric values, assume they are durations
        elif isinstance(first, (int, float)):
            try:
                return float(sum(x for x in lst if isinstance(x, (int, float))))
            except Exception:
                pass

        # Final fallback: try second element of last entry
        try:
            last = lst[-1]
            if isinstance(last, (list, tuple)) and len(last) >= 2 and isinstance(last[1], (int, float)):
                return float(last[1])
        except Exception:
            pass

        return 0.0

    def _compute_remaining_work(self) -> float:
        try:
            total_duration = float(self.task_duration)
        except Exception:
            return 0.0
        done = self._compute_done_work()
        remaining = total_duration - done
        if remaining < 0.0:
            return 0.0
        return remaining

    def _initialize_margin_if_needed(self):
        if getattr(self, "_margin_seconds", None) is not None:
            return

        try:
            step = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        except Exception:
            step = 0.0
        try:
            oh = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        except Exception:
            oh = 0.0

        base_margin = 2.0 * max(step, oh, 1.0)  # at least a small positive margin

        try:
            deadline = float(self.deadline)
            task_duration = float(self.task_duration)
            slack = max(deadline - task_duration, 0.0)
        except Exception:
            slack = 0.0

        if slack > 0.0:
            max_margin = 0.5 * slack
            margin = min(base_margin, max_margin)
        else:
            margin = base_margin

        if margin <= 0.0:
            margin = max(step, oh, 1.0)

        self._margin_seconds = margin

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not hasattr(self, "force_on_demand"):
            self.force_on_demand = False
            self._margin_seconds = None

        # If we've already committed to on-demand, always stay on-demand
        if self.force_on_demand:
            return ClusterType.ON_DEMAND

        remaining_work = self._compute_remaining_work()
        if remaining_work <= 0.0:
            # Task is effectively done; no need to spend more
            return ClusterType.NONE

        self._initialize_margin_if_needed()

        try:
            elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        except Exception:
            elapsed = 0.0
        try:
            deadline = float(self.deadline)
        except Exception:
            # If deadline is not available, fall back to always using spot when available
            if has_spot:
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND

        time_remaining = deadline - elapsed
        if time_remaining <= 0.0:
            # Already at/after deadline; best effort is to use on-demand
            self.force_on_demand = True
            return ClusterType.ON_DEMAND

        try:
            restart_oh = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        except Exception:
            restart_oh = 0.0

        required_for_on_demand = remaining_work + restart_oh + (self._margin_seconds or 0.0)

        # Decide whether we must now commit to on-demand to safely hit the deadline
        if time_remaining <= required_for_on_demand:
            self.force_on_demand = True
            return ClusterType.ON_DEMAND

        # Still have slack: prefer spot when available, otherwise pause
        if has_spot:
            return ClusterType.SPOT

        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
