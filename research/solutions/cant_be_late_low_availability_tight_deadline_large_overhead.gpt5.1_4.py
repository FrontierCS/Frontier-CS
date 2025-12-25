import math
from typing import Optional

try:
    from sky_spot.strategies.strategy import Strategy
    from sky_spot.utils import ClusterType
except ImportError:  # Fallbacks for local testing without the real package
    from enum import Enum

    class ClusterType(Enum):
        SPOT = 1
        ON_DEMAND = 2
        NONE = 3

    class Strategy:
        def __init__(self, *args, **kwargs):
            self.env = None
            self.task_duration = 0.0
            self.task_done_time = []
            self.deadline = 0.0
            self.restart_overhead = 0.0


class Solution(Strategy):
    NAME = "cant_be_late_v1"

    def solve(self, spec_path: str) -> "Solution":
        # Global initialization (once per evaluator run)
        self.force_on_demand: bool = False
        self._task_done_sum: float = 0.0
        self._last_task_done_count: int = 0
        self._prev_elapsed: Optional[float] = None
        self._last_env_id: Optional[int] = None
        self._margin_initialized: bool = False
        self.safety_margin_seconds: float = 60.0
        return self

    def _reset_episode_state_if_needed(self) -> None:
        """Detect new evaluation episode and reset per-episode state."""
        env = getattr(self, "env", None)
        if env is None:
            return

        env_id = id(env)
        elapsed = float(getattr(env, "elapsed_seconds", 0.0))

        if (
            self._last_env_id is None
            or env_id != self._last_env_id
            or (self._prev_elapsed is not None and elapsed < self._prev_elapsed)
        ):
            # New episode or new environment instance
            self.force_on_demand = False
            self._task_done_sum = 0.0
            self._last_task_done_count = 0
            self._margin_initialized = False

        self._last_env_id = env_id
        self._prev_elapsed = elapsed

    def _update_task_done_sum(self) -> None:
        """Efficiently maintain running sum of task_done_time segments."""
        times_list = getattr(self, "task_done_time", None)
        if times_list is None:
            self._task_done_sum = 0.0
            self._last_task_done_count = 0
            return
        l = len(times_list)
        if l > self._last_task_done_count:
            # Sum only newly added segments
            self._task_done_sum += sum(times_list[self._last_task_done_count : l])
            self._last_task_done_count = l

    def _ensure_margin_initialized(self) -> None:
        if not self._margin_initialized:
            gap = float(self.env.gap_seconds)
            # At least 60s, at least half a step
            self.safety_margin_seconds = max(60.0, 0.5 * gap)
            self._margin_initialized = True

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Per-episode reset if needed
        self._reset_episode_state_if_needed()
        self._update_task_done_sum()
        self._ensure_margin_initialized()

        env = self.env
        elapsed = float(env.elapsed_seconds)
        gap = float(env.gap_seconds)
        deadline = float(self.deadline)
        overhead = float(self.restart_overhead)
        margin = float(self.safety_margin_seconds)

        remaining_work = float(self.task_duration) - self._task_done_sum
        if remaining_work <= 0.0:
            return ClusterType.NONE

        time_to_deadline = deadline - elapsed

        # If we've already committed to on-demand, keep using it.
        if self.force_on_demand:
            return ClusterType.ON_DEMAND

        # If there's not even one full step until the deadline, must use on-demand now.
        if time_to_deadline <= gap:
            self.force_on_demand = True
            return ClusterType.ON_DEMAND

        # Decide whether we can afford one more speculative step (SPOT or NONE).
        # Safe to speculate only if, after spending 'gap' seconds with zero guaranteed
        # progress, there is still enough time to finish the remaining work on
        # on-demand including one restart_overhead and a safety margin.
        if remaining_work + overhead + margin > time_to_deadline - gap:
            self.force_on_demand = True
            return ClusterType.ON_DEMAND

        # Speculative phase: use SPOT when available, otherwise wait.
        if has_spot:
            return ClusterType.SPOT
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)