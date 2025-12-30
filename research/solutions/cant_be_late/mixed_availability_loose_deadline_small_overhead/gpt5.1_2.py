import math
from typing import Any, Tuple, List, Union

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


Number = Union[int, float]


class Solution(Strategy):
    NAME = "cant_be_late_heuristic_v1"

    def solve(self, spec_path: str) -> "Solution":
        return self

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls()

    def _initialize_policy(self) -> None:
        if getattr(self, "_policy_initialized", False):
            return
        self._policy_initialized = True

        # Basic environment parameters with safe defaults
        self._restart_overhead: float = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        self._task_duration: float = float(getattr(self, "task_duration", 0.0) or 0.0)
        self._deadline: float = float(getattr(self, "deadline", 0.0) or 0.0)

        env = getattr(self, "env", None)
        gap_seconds: float = 1.0
        if env is not None:
            gap_seconds = float(getattr(env, "gap_seconds", 1.0) or 1.0)

        initial_slack: float = max(self._deadline - self._task_duration, 0.0)

        # Urgent slack: below this, we commit to on-demand only
        rel_urgent: float = 0.15 * initial_slack
        abs_urgent: float = 5.0 * self._restart_overhead + 2.0 * gap_seconds
        urgent: float = max(rel_urgent, abs_urgent)
        if initial_slack > 0.0:
            urgent = min(urgent, 0.7 * initial_slack)
        self._urgent_slack: float = max(urgent, 0.0)

        # Idle slack: above this, when spot is unavailable we may idle instead of using OD
        rel_idle: float = 0.5 * initial_slack
        idle: float = max(2.0 * self._urgent_slack, rel_idle)
        if initial_slack > 0.0:
            idle = min(idle, 0.9 * initial_slack)
        self._idle_slack: float = max(idle, self._urgent_slack)

        self._force_on_demand: bool = False

    def _compute_done_seconds(self) -> float:
        segments = getattr(self, "task_done_time", None)
        if not segments:
            return 0.0

        total: float = 0.0
        for seg in segments:
            dur: float = 0.0
            if isinstance(seg, (int, float)):
                dur = float(seg)
            elif isinstance(seg, (tuple, list)) and len(seg) >= 2:
                try:
                    dur = float(seg[1]) - float(seg[0])
                except Exception:
                    dur = 0.0
            else:
                if hasattr(seg, "duration"):
                    try:
                        dur = float(seg.duration)
                    except Exception:
                        dur = 0.0
                elif hasattr(seg, "end_time") and hasattr(seg, "start_time"):
                    try:
                        dur = float(seg.end_time) - float(seg.start_time)
                    except Exception:
                        dur = 0.0
            if dur > 0.0:
                total += dur
        return total

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._initialize_policy()

        done: float = self._compute_done_seconds()
        remaining: float = max(self._task_duration - done, 0.0)

        # If task is already complete, no need to run anything
        if remaining <= 0.0:
            return ClusterType.NONE

        now: float = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        time_left: float = self._deadline - now

        # If somehow past deadline, just push on-demand
        if time_left <= 0.0:
            return ClusterType.ON_DEMAND

        extra_slack: float = time_left - remaining

        # If we've committed to on-demand, never go back to spot
        if self._force_on_demand:
            return ClusterType.ON_DEMAND

        # Enter panic mode when slack is small
        if extra_slack <= self._urgent_slack:
            self._force_on_demand = True
            return ClusterType.ON_DEMAND

        # Non-panic modes:
        # Prefer spot when available
        if has_spot:
            return ClusterType.SPOT

        # Spot unavailable: decide between idling and on-demand
        if extra_slack >= self._idle_slack:
            # Plenty of slack left: we can wait for cheaper spot
            return ClusterType.NONE

        # Moderate slack: use on-demand when spot unavailable
        return ClusterType.ON_DEMAND