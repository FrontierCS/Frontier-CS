import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Cant-Be-Late multi-region scheduling strategy."""

    NAME = "cb_late_safe_spot_v1"

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
        self._init_strategy_state()
        return self

    def _init_strategy_state(self):
        # Per-scenario state initialization
        self._commit_on_demand = False
        self._last_elapsed_seconds = getattr(self.env, "elapsed_seconds", 0.0)
        task_done_time = getattr(self, "task_done_time", [])
        self._last_segments_len = len(task_done_time)
        self._done_cache = float(sum(task_done_time)) if task_done_time else 0.0

    def _update_done_cache(self):
        """Incrementally maintain total work done to avoid O(n) per step."""
        task_done_time = self.task_done_time
        cur_len = len(task_done_time)
        if cur_len > self._last_segments_len:
            new_sum = 0.0
            for i in range(self._last_segments_len, cur_len):
                new_sum += task_done_time[i]
            self._done_cache += new_sum
            self._last_segments_len = cur_len
        return self._done_cache

    def _maybe_reset_state(self):
        """Detect environment reset and reinitialize state if needed."""
        current_elapsed = getattr(self.env, "elapsed_seconds", 0.0)
        # If time went backwards, it's a new scenario.
        if not hasattr(self, "_last_elapsed_seconds") or current_elapsed < self._last_elapsed_seconds:
            self._init_strategy_state()
        self._last_elapsed_seconds = current_elapsed

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Detect new scenario and reset internal state if necessary.
        self._maybe_reset_state()

        # Update cached work done
        done_work = self._update_done_cache()

        # If task already completed, do nothing more.
        if done_work >= self.task_duration:
            return ClusterType.NONE

        # Once committed, stay on on-demand until completion.
        if self._commit_on_demand:
            return ClusterType.ON_DEMAND

        remaining_work = self.task_duration - done_work
        time_left = self.deadline - self.env.elapsed_seconds

        # If somehow out of time, best effort: switch to on-demand.
        if time_left <= 0.0:
            self._commit_on_demand = True
            return ClusterType.ON_DEMAND

        # Conservative overhead budget: existing pending overhead plus one
        # fresh restart when we finally settle on on-demand.
        remaining_restart = getattr(self.env, "remaining_restart_overhead", 0.0)
        overhead_budget = self.restart_overhead + max(0.0, remaining_restart)

        required_time = remaining_work + overhead_budget
        gap = self.env.gap_seconds

        # It is only safe to "gamble" one more step on non-guaranteed progress
        # (Spot or idle) if, even after an entire gap with zero progress,
        # we could still finish using on-demand.
        if time_left <= required_time + gap:
            self._commit_on_demand = True
            return ClusterType.ON_DEMAND

        # Safe region: prefer spot when available, otherwise idle to save cost.
        if has_spot:
            return ClusterType.SPOT

        return ClusterType.NONE