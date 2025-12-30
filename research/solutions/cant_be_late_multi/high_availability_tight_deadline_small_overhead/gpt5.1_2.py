import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy with hard-deadline guarantee."""

    NAME = "cant_be_late_strategy"

    def solve(self, spec_path: str) -> "Solution":
        with open(spec_path) as f:
            config = json.load(f)

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)
        return self

    # ---------- Internal helpers ----------

    def _initialize_if_needed(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._initialized = True

        # Initialize completed work tracking.
        td_list = getattr(self, "task_done_time", None)
        if td_list:
            self._last_task_done_len = len(td_list)
            self._completed_work = float(sum(td_list))
        else:
            self._last_task_done_len = 0
            self._completed_work = 0.0

        # Helper to extract scalar seconds from possibly list-valued fields.
        def _to_scalar_seconds(value, default=0.0):
            if isinstance(value, (list, tuple)):
                if not value:
                    return float(default)
                value = value[0]
            try:
                return float(value)
            except (TypeError, ValueError):
                return float(default)

        # Cache key configuration values in seconds.
        self._task_duration_total = _to_scalar_seconds(
            getattr(self, "task_duration", None), default=0.0
        )
        self._restart_overhead = _to_scalar_seconds(
            getattr(self, "restart_overhead", None), default=0.0
        )
        self._deadline = _to_scalar_seconds(
            getattr(self, "deadline", None), default=0.0
        )

        gap = getattr(self.env, "gap_seconds", None)
        if gap is None:
            gap = 60.0  # fallback
        self._gap_seconds = float(gap)

        # Safety slack to guarantee deadline even with restart overhead
        base_margin = max(self._restart_overhead, self._gap_seconds)
        # Large enough to cover worst-case single-step slack drop and restart.
        self._safe_slack = 4.0 * base_margin + self._restart_overhead

        self._force_on_demand = False

    def _update_completed_work(self) -> None:
        td_list = getattr(self, "task_done_time", None)
        if not td_list:
            return
        curr_len = len(td_list)
        if curr_len > self._last_task_done_len:
            new_segments = td_list[self._last_task_done_len : curr_len]
            # Each segment is work-time in seconds.
            self._completed_work += float(sum(new_segments))
            self._last_task_done_len = curr_len

    # ---------- Core decision logic ----------

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._initialize_if_needed()
        self._update_completed_work()

        remaining_work = self._task_duration_total - self._completed_work
        if remaining_work <= 0.0:
            # Job complete: avoid incurring any more cost.
            return ClusterType.NONE

        elapsed = float(self.env.elapsed_seconds)
        time_left = self._deadline - elapsed

        if time_left <= 0.0:
            # Past deadline; nothing can fix lateness, but run ON_DEMAND to finish ASAP.
            self._force_on_demand = True
            return ClusterType.ON_DEMAND

        slack = time_left - remaining_work

        if slack <= 0.0:
            # Already behind ideal schedule: must use ON_DEMAND exclusively.
            self._force_on_demand = True

        # If we're close enough to the deadline that only ON_DEMAND can safely finish in time,
        # permanently switch to ON_DEMAND.
        if not self._force_on_demand and slack <= self._safe_slack:
            self._force_on_demand = True

        if self._force_on_demand:
            return ClusterType.ON_DEMAND

        # Plenty of slack left: use cheap SPOT when available, otherwise wait.
        if has_spot:
            return ClusterType.SPOT
        else:
            return ClusterType.NONE