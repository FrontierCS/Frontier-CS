import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy focusing on meeting deadline with minimal on-demand usage."""

    NAME = "my_strategy"

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

        # Cross-episode state
        self._last_elapsed = None
        self._episode_initialized = False

        # Per-episode cached state (initialized in _reset_episode_state)
        self._use_on_demand = False
        self._cached_done = 0.0
        self._last_task_done_len = 0
        self._gap_seconds = 0.0
        self._restart_overhead = 0.0
        self._delta_spot_max = 0.0
        self._delta_none_max = 0.0
        self._total_work_seconds = 0.0
        self._deadline_seconds = 0.0

        return self

    def _reset_episode_state(self):
        """Reset per-episode state; called when a new trace/episode starts."""
        self._episode_initialized = True
        self._use_on_demand = False
        self._cached_done = 0.0
        self._last_task_done_len = 0

        # Cache environment and problem constants (in seconds)
        self._gap_seconds = float(getattr(self.env, "gap_seconds", 0.0))

        ro = getattr(self, "restart_overhead", 0.0)
        if isinstance(ro, (list, tuple)):
            ro = ro[0]
        self._restart_overhead = float(ro)

        td = getattr(self, "task_duration", 0.0)
        if isinstance(td, (list, tuple)):
            td = td[0]
        self._total_work_seconds = float(td)

        dl = getattr(self, "deadline", 0.0)
        if isinstance(dl, (list, tuple)):
            dl = dl[0]
        self._deadline_seconds = float(dl)

        # Conservative upper bounds on elapsed time per step
        # For spot: at most one full gap plus one restart overhead if preempted
        self._delta_spot_max = self._gap_seconds + self._restart_overhead
        # For NONE: at most one full gap of wall-clock time without progress
        self._delta_none_max = self._gap_seconds

    def _update_work_done_cache(self):
        """Incrementally maintain sum(self.task_done_time) in O(1) amortized time."""
        td = self.task_done_time
        l = len(td)
        if l > self._last_task_done_len:
            self._cached_done += sum(td[self._last_task_done_len:l])
            self._last_task_done_len = l

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Detect new episode by elapsed time reset
        current_elapsed = float(self.env.elapsed_seconds)
        if self._last_elapsed is None or current_elapsed < self._last_elapsed:
            self._reset_episode_state()
        self._last_elapsed = current_elapsed

        # Update cached completed work
        self._update_work_done_cache()
        work_done = self._cached_done

        total_work = self._total_work_seconds
        work_remaining = max(total_work - work_done, 0.0)

        # If task already finished, do nothing further
        if work_remaining <= 0.0:
            return ClusterType.NONE

        # If we've already committed to on-demand, always stay there
        if self._use_on_demand:
            return ClusterType.ON_DEMAND

        # Time left until deadline
        time_left = max(self._deadline_seconds - current_elapsed, 0.0)

        # Conservative overhead to switch to on-demand
        od_overhead = self._restart_overhead

        # If even switching to on-demand immediately may not be enough,
        # still choose on-demand as best-effort.
        if time_left <= work_remaining + od_overhead:
            self._use_on_demand = True
            return ClusterType.ON_DEMAND

        # Decision when spot is available
        if has_spot:
            # Maximum time we might lose this step if we choose spot but gain no progress
            delta_max = self._delta_spot_max

            # Only use spot if we can afford to potentially waste delta_max time
            # and still finish on-demand afterwards.
            if time_left <= work_remaining + od_overhead + delta_max:
                # Not enough slack to safely risk another spot step
                self._use_on_demand = True
                return ClusterType.ON_DEMAND

            # Safe to continue on spot
            return ClusterType.SPOT

        # Spot not available: consider idling (NONE) vs. switching to on-demand
        delta_max = self._delta_none_max

        # If we can't afford to lose one idle gap, switch to on-demand now
        if time_left <= work_remaining + od_overhead + delta_max:
            self._use_on_demand = True
            return ClusterType.ON_DEMAND

        # Otherwise, wait for spot to return
        return ClusterType.NONE