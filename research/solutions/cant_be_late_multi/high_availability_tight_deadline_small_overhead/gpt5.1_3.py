import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy with safe on-demand fallback."""

    NAME = "my_strategy"

    def solve(self, spec_path: str) -> "Solution":
        with open(spec_path) as f:
            config = json.load(f)

        # Initialize base strategy (environment, etc.)
        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)

        # Internal state initialization
        self._init_internal_state(config)
        return self

    def _init_internal_state(self, config) -> None:
        # Normalize times to seconds using both config and (if present) base attributes.
        self._deadline = self._normalize_time(getattr(self, "deadline", None), config["deadline"])
        self._task_duration = self._normalize_time(
            getattr(self, "task_duration", None), config["duration"]
        )
        self._restart_overhead = self._normalize_time(
            getattr(self, "restart_overhead", None), config["overhead"]
        )

        # Progress tracking (avoid O(n^2) summations)
        self._progress_done = 0.0
        self._last_task_done_len = len(getattr(self, "task_done_time", []))

        # Control flags
        self._committed_od = False
        self._finished = False

    @staticmethod
    def _normalize_time(env_value, conf_hours) -> float:
        """Return time in seconds, reconciling config (hours) with env value if present."""
        conf_hours_f = float(conf_hours)
        conf_secs = conf_hours_f * 3600.0

        if env_value is None:
            return conf_secs

        try:
            v = float(env_value)
        except (TypeError, ValueError):
            return conf_secs

        if conf_secs > 0:
            # If env already uses seconds
            if abs(v - conf_secs) <= 1e-3 * conf_secs:
                return v
            # If env uses hours
            if abs(v * 3600.0 - conf_secs) <= 1e-3 * conf_secs:
                return v * 3600.0

        return conf_secs

    def _update_progress(self) -> None:
        """Incrementally update total work progress from task_done_time list."""
        segments = getattr(self, "task_done_time", None)
        if not segments:
            return
        n = len(segments)
        if n <= self._last_task_done_len:
            return
        added = 0.0
        # Typically this loop runs once per step (one new segment).
        for i in range(self._last_task_done_len, n):
            added += segments[i]
        self._progress_done += added
        self._last_task_done_len = n

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update observed progress.
        self._update_progress()

        # Check if task is already complete.
        if (not self._finished) and (self._progress_done >= self._task_duration - 1e-6):
            self._finished = True

        if self._finished:
            return ClusterType.NONE

        # Time and work remaining (in seconds).
        elapsed = getattr(self.env, "elapsed_seconds", 0.0)
        time_left = self._deadline - elapsed
        if time_left <= 0.0:
            # Deadline already passed; no action can fix this, so avoid extra cost.
            return ClusterType.NONE

        remaining_work = self._task_duration - self._progress_done
        if remaining_work < 0.0:
            remaining_work = 0.0

        # If we've already committed to on-demand, stay there to avoid further restarts.
        if self._committed_od:
            return ClusterType.ON_DEMAND

        gap = getattr(self.env, "gap_seconds", 0.0)
        overhead = self._restart_overhead

        # Safe commit condition:
        # If we kept using only spot/idle for one more step with zero progress,
        # we must still have enough time afterwards to finish entirely on on-demand.
        # That implies: time_left - gap >= remaining_work + overhead  (worst case)
        # <=> time_left >= remaining_work + overhead + gap
        # If this no longer holds, we must commit now.
        if time_left <= remaining_work + overhead + gap + 1e-6:
            self._committed_od = True
            return ClusterType.ON_DEMAND

        # Speculative phase: prefer Spot when available, otherwise idle (no cluster).
        if has_spot:
            return ClusterType.SPOT

        return ClusterType.NONE