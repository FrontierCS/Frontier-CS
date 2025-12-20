import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_fallback_v1"

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
        # Internal state
        self._commit_on_demand = False
        self._done_sum = 0.0
        self._last_len = 0
        return self

    def _update_progress_cache(self):
        l = len(self.task_done_time)
        if l > self._last_len:
            # Incremental sum of new segments
            self._done_sum += sum(self.task_done_time[self._last_len:])
            self._last_len = l

    def _safe_progress_for_choice(self, choose_type: ClusterType, last_type: ClusterType, g: float) -> float:
        # Progress realized in the current step if we choose choose_type
        # Overhead rules:
        # - If we continue with the same type as last step, progress = g - remaining_restart_overhead (clipped at 0)
        # - If we switch types (or from NONE), progress = g - restart_overhead (clipped at 0)
        if choose_type == last_type and choose_type != ClusterType.NONE:
            overhead = getattr(self, "remaining_restart_overhead", 0.0) or 0.0
        else:
            overhead = self.restart_overhead
        prog = g - overhead
        return prog if prog > 0.0 else 0.0

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update cached progress
        self._update_progress_cache()

        # If done, no need to run further
        remaining_work = self.task_duration - self._done_sum
        if remaining_work <= 0.0:
            return ClusterType.NONE

        g = self.env.gap_seconds
        T = self.deadline - self.env.elapsed_seconds  # time remaining

        # If we've committed to on-demand, stick with it
        if self._commit_on_demand:
            return ClusterType.ON_DEMAND

        # Helper to decide safe postponement
        # After taking an action this step, time left = T - g
        # To be safe for fallback next step (worst-case), require:
        # (T - g) >= (remaining_work_after_step) + restart_overhead
        # since starting OD next step will incur overhead.
        if has_spot:
            # Consider running on spot this step
            progress_now_spot = self._safe_progress_for_choice(ClusterType.SPOT, last_cluster_type, g)
            T_after = T - g
            S_after = remaining_work - progress_now_spot
            if S_after < 0.0:
                S_after = 0.0
            if T_after >= S_after + self.restart_overhead:
                return ClusterType.SPOT
            else:
                # Not safe to spend this step on spot; commit to OD now
                self._commit_on_demand = True
                return ClusterType.ON_DEMAND
        else:
            # Spot unavailable: decide to idle or start OD
            T_after = T - g
            # If we idle, remaining work unchanged; next step starting OD incurs overhead
            if T_after >= remaining_work + self.restart_overhead:
                return ClusterType.NONE
            else:
                self._commit_on_demand = True
                return ClusterType.ON_DEMAND
