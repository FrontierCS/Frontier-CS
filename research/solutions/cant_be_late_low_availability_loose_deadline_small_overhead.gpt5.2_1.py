import math
from typing import Any, Iterable, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_v1"

    def __init__(self, args=None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except Exception:
                pass
        self.args = args
        self._on_demand_mode = False
        self._overhead_left = 0.0
        self._prev_choice = None
        self._last_progress = 0.0

    def solve(self, spec_path: str) -> "Solution":
        return self

    @staticmethod
    def _is_num(x: Any) -> bool:
        return isinstance(x, (int, float)) and not (isinstance(x, float) and (math.isnan(x) or math.isinf(x)))

    def _progress_done_seconds(self) -> float:
        tdt = getattr(self, "task_done_time", None)
        if tdt is None:
            return 0.0
        if self._is_num(tdt):
            return float(tdt)
        if isinstance(tdt, (list, tuple)):
            total = 0.0
            for item in tdt:
                if self._is_num(item):
                    total += float(item)
                    continue
                if isinstance(item, (list, tuple)) and len(item) >= 2 and self._is_num(item[0]) and self._is_num(item[1]):
                    a = float(item[0])
                    b = float(item[1])
                    if b >= a:
                        total += (b - a)
                    else:
                        total += b
                    continue
                try:
                    fv = float(item)
                    if self._is_num(fv):
                        total += float(fv)
                except Exception:
                    pass
            return float(total)
        try:
            fv = float(tdt)
            return float(fv) if self._is_num(fv) else 0.0
        except Exception:
            return 0.0

    def _safety_margin(self) -> float:
        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        # Conservative but small relative to the 22h slack in the benchmark.
        # Keep bounded in case gap is very large.
        base = min(max(gap, 0.0), 1800.0)  # cap at 30 minutes
        return (2.0 * overhead) + base + 1.0

    def _simulate_one_step(
        self,
        action: ClusterType,
        last_cluster_type: ClusterType,
        has_spot: bool,
        remaining_work: float,
        time_left: float,
    ):
        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        if action == ClusterType.SPOT and not has_spot:
            return None

        if action == ClusterType.NONE:
            progress = 0.0
            overhead_after = 0.0
        else:
            if action == last_cluster_type:
                overhead_start = float(self._overhead_left)
            else:
                overhead_start = overhead
            progress = max(0.0, gap - overhead_start)
            overhead_after = max(0.0, overhead_start - gap)

        remaining_work_next = max(0.0, remaining_work - progress)
        time_left_next = time_left - gap

        return remaining_work_next, time_left_next, overhead_after

    def _feasible_after_action(
        self,
        action: ClusterType,
        last_cluster_type: ClusterType,
        has_spot: bool,
        remaining_work: float,
        time_left: float,
    ) -> bool:
        sim = self._simulate_one_step(action, last_cluster_type, has_spot, remaining_work, time_left)
        if sim is None:
            return False
        remaining_work_next, time_left_next, overhead_after = sim
        if remaining_work_next <= 0.0:
            return True
        overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        if action == ClusterType.ON_DEMAND:
            required = remaining_work_next + float(overhead_after)
        else:
            required = remaining_work_next + overhead

        return time_left_next >= (required + self._safety_margin())

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        time_left = deadline - elapsed

        progress_done = self._progress_done_seconds()
        remaining_work = max(0.0, task_duration - progress_done)

        # If done, stop spending.
        if remaining_work <= 0.0:
            self._on_demand_mode = False
            self._overhead_left = 0.0
            self._prev_choice = ClusterType.NONE
            return ClusterType.NONE

        # If we have committed to on-demand, keep it until completion.
        if self._on_demand_mode:
            # Update overhead estimate for next step (if needed).
            gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
            overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)
            if last_cluster_type == ClusterType.ON_DEMAND:
                overhead_start = float(self._overhead_left)
            else:
                overhead_start = overhead
            self._overhead_left = max(0.0, overhead_start - gap)
            self._prev_choice = ClusterType.ON_DEMAND
            return ClusterType.ON_DEMAND

        # Candidate actions by preference:
        # - If spot is available: use it (cheap progress), otherwise do nothing (avoid burning on-demand).
        # - Fall back to on-demand only when necessary for feasibility.
        if has_spot:
            preferred = [ClusterType.SPOT, ClusterType.NONE, ClusterType.ON_DEMAND]
        else:
            preferred = [ClusterType.NONE, ClusterType.ON_DEMAND]

        choice = None
        for action in preferred:
            if action == ClusterType.SPOT and not has_spot:
                continue
            if self._feasible_after_action(action, last_cluster_type, has_spot, remaining_work, time_left):
                choice = action
                break

        if choice is None:
            choice = ClusterType.ON_DEMAND

        if choice == ClusterType.ON_DEMAND:
            self._on_demand_mode = True

        # Update internal overhead estimate for next step.
        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        if choice == ClusterType.NONE:
            self._overhead_left = 0.0
        else:
            if choice == last_cluster_type:
                overhead_start = float(self._overhead_left)
            else:
                overhead_start = overhead
            self._overhead_left = max(0.0, overhead_start - gap)

        self._prev_choice = choice
        self._last_progress = progress_done
        return choice

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)