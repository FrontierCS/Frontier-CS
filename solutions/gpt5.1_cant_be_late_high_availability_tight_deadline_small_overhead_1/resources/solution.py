import math
from typing import Any

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        try:
            super().__init__(*args, **kwargs)
        except TypeError:
            try:
                super().__init__()  # type: ignore
            except TypeError:
                pass
        self._params_inited = False
        self._force_on_demand = False
        self._gap = 1.0
        self._restart_overhead = 0.0
        self._initial_slack = 0.0
        self._reserve_slack = 0.0
        self._spot_threshold = 0.0
        self._idle_threshold = 0.0
        self._tail_threshold = 0.0

    def solve(self, spec_path: str) -> "Solution":
        return self

    @classmethod
    def _from_args(cls, parser) -> "Solution":
        args, _ = parser.parse_known_args()
        return cls(args)

    def _initialize_params(self) -> None:
        self._params_inited = True
        env = getattr(self, "env", None)
        gap = float(getattr(env, "gap_seconds", 1.0))
        ro = float(getattr(self, "restart_overhead", 0.0))
        deadline = float(getattr(self, "deadline", 0.0))
        task_duration = float(getattr(self, "task_duration", 0.0))
        initial_slack = max(deadline - task_duration, 0.0)

        self._gap = max(gap, 1e-3)
        self._restart_overhead = max(ro, 0.0)
        self._initial_slack = initial_slack

        if initial_slack > 0.0:
            base_reserve = max(
                3.0 * self._gap,
                2.0 * self._restart_overhead,
                0.1 * initial_slack,
            )
            max_reserve = 0.5 * initial_slack
            reserve = min(base_reserve, max_reserve)
        else:
            reserve = max(3.0 * self._gap, 2.0 * self._restart_overhead)

        if reserve < 0.0:
            reserve = 0.0

        self._reserve_slack = reserve
        self._spot_threshold = self._reserve_slack + 1.5 * self._restart_overhead + 2.0 * self._gap
        self._idle_threshold = self._reserve_slack
        self._tail_threshold = max(2.0 * self._restart_overhead, 3.0 * self._gap)

    def _compute_work_done(self) -> float:
        tdt = getattr(self, "task_done_time", None)
        if not tdt:
            return 0.0
        total = 0.0
        for seg in tdt:
            try:
                if isinstance(seg, (int, float)):
                    dur = float(seg)
                    if dur > 0.0:
                        total += dur
                elif isinstance(seg, (tuple, list)):
                    if len(seg) >= 2:
                        start, end = seg[0], seg[1]
                        if start is not None and end is not None:
                            dur = float(end) - float(start)
                            if dur > 0.0:
                                total += dur
                else:
                    if hasattr(seg, "duration"):
                        dur = float(seg.duration)
                        if dur > 0.0:
                            total += dur
                    elif hasattr(seg, "start") and hasattr(seg, "end"):
                        dur = float(seg.end) - float(seg.start)
                        if dur > 0.0:
                            total += dur
            except Exception:
                continue
        task_duration = float(getattr(self, "task_duration", 0.0))
        if task_duration > 0.0:
            total = min(total, task_duration)
        return max(total, 0.0)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not self._params_inited:
            self._initialize_params()

        task_duration = float(getattr(self, "task_duration", 0.0))
        work_done = self._compute_work_done()
        remaining_work = max(task_duration - work_done, 0.0)

        if remaining_work <= 0.0:
            return ClusterType.NONE

        env = getattr(self, "env", None)
        elapsed = float(getattr(env, "elapsed_seconds", 0.0))
        deadline = float(getattr(self, "deadline", 0.0))
        time_remaining = max(deadline - elapsed, 0.0)

        if time_remaining <= 0.0:
            return ClusterType.ON_DEMAND

        slack = time_remaining - remaining_work

        if slack < 0.0:
            self._force_on_demand = True
            return ClusterType.ON_DEMAND

        if remaining_work <= self._tail_threshold:
            self._force_on_demand = True
            return ClusterType.ON_DEMAND

        if self._force_on_demand:
            return ClusterType.ON_DEMAND

        if slack <= self._spot_threshold:
            self._force_on_demand = True
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        if slack > self._idle_threshold:
            return ClusterType.NONE

        self._force_on_demand = True
        return ClusterType.ON_DEMAND
