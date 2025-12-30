import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Cant-Be-Late Multi-Region Scheduling Strategy."""

    NAME = "cant_be_late_heuristic_v1"

    def solve(self, spec_path: str) -> "Solution":
        """Initialize the solution from spec_path config."""
        with open(spec_path) as f:
            config = json.load(f)

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)

        # Internal runtime state (initialized lazily in _step once env is ready)
        self._initialized_runtime = False
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """Decide next action based on current state."""
        # Lazy initialization since env is available only after __init__
        if not getattr(self, "_initialized_runtime", False):
            self._initialized_runtime = True

            # Task duration (seconds) as a scalar
            td_attr = getattr(self, "task_duration", 0.0)
            if isinstance(td_attr, (list, tuple)):
                self._task_duration_total = float(sum(td_attr))
            else:
                self._task_duration_total = float(td_attr)

            # Cached work-done accumulator to avoid O(n) sum every step
            self._work_done = 0.0
            self._last_task_done_len = 0

            # Gap size (seconds) for each timestep
            gap = getattr(self.env, "gap_seconds", 0.0)
            if not isinstance(gap, (int, float)) or gap <= 0:
                gap = 1.0
            self._gap = float(gap)

            # Whether we've entered the conservative on-demand-only phase
            self._on_demand_only = False

        # Incrementally update accumulated work
        td_list = self.task_done_time
        cur_len = len(td_list)
        if cur_len > self._last_task_done_len:
            # Only sum newly added segments
            self._work_done += sum(td_list[self._last_task_done_len:cur_len])
            self._last_task_done_len = cur_len

        # Remaining work (seconds)
        remaining_work = self._task_duration_total - self._work_done
        if remaining_work <= 0.0:
            # Task is already complete; no need to run more
            return ClusterType.NONE

        # Time remaining until deadline (seconds)
        t_elapsed = self.env.elapsed_seconds
        time_remaining = self.deadline - t_elapsed

        if time_remaining <= 0.0:
            # Already at / past deadline: run On-Demand to minimize further lateness
            return ClusterType.ON_DEMAND

        # Safety margin: one full timestep of potential wasted time plus one restart overhead.
        # This guarantees that even if the next step yields no progress (or a restart),
        # we can still switch to On-Demand and finish by the deadline.
        safety_margin = self.restart_overhead + self._gap

        # Enter conservative on-demand-only mode if we no longer have slack
        if (not self._on_demand_only) and time_remaining <= remaining_work + safety_margin:
            self._on_demand_only = True

        if self._on_demand_only:
            # From this point on, always use On-Demand to guarantee completion
            return ClusterType.ON_DEMAND

        # Spot-preferred mode:
        # - Use Spot when available (cheapest progress).
        # - If Spot isn't available, pause (NONE) to avoid expensive On-Demand
        #   while we still have ample slack before the deadline.
        if has_spot:
            return ClusterType.SPOT
        else:
            return ClusterType.NONE