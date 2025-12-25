import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cbm_gap_safety_v1"

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

        # Internal state for efficiency and control
        self._sum_done = 0.0
        self._last_td_len = 0
        self._locked_to_on_demand = False
        self._last_elapsed_seen = -1.0
        self._no_spot_consecutive = 0
        self._initialized = False
        return self

    def _maybe_reset_state(self):
        # Reset between scenarios/episodes if elapsed resets to 0
        if not self._initialized or self.env.elapsed_seconds == 0.0 or self._last_elapsed_seen > self.env.elapsed_seconds:
            self._sum_done = 0.0
            self._last_td_len = 0
            self._locked_to_on_demand = False
            self._no_spot_consecutive = 0
            self._initialized = True

    def _update_progress_cache(self):
        # Efficiently update the sum of task_done_time incrementally
        curr_len = len(self.task_done_time)
        if curr_len > self._last_td_len:
            # Only sum newly appended segments
            newly_added = self.task_done_time[self._last_td_len:curr_len]
            if newly_added:
                self._sum_done += float(sum(newly_added))
            self._last_td_len = curr_len

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._maybe_reset_state()
        self._update_progress_cache()

        # Record elapsed for reset detection
        self._last_elapsed_seen = self.env.elapsed_seconds

        # Compute core metrics
        remaining_work = max(0.0, float(self.task_duration) - self._sum_done)
        time_left = max(0.0, float(self.deadline) - float(self.env.elapsed_seconds))
        gap = float(self.env.gap_seconds)
        overhead = float(self.restart_overhead)

        # Update consecutive no-spot counter
        if has_spot:
            self._no_spot_consecutive = 0
        else:
            self._no_spot_consecutive += 1

        # Decide if we must lock to on-demand to guarantee deadline
        # Safety rule: if slack <= overhead + 1 gap, pivot to OD now to survive a worst-case lost step
        if not self._locked_to_on_demand:
            if time_left <= remaining_work + overhead + gap:
                self._locked_to_on_demand = True

        # If locked, always use on-demand
        if self._locked_to_on_demand:
            return ClusterType.ON_DEMAND

        # Opportunistically use spot if available; otherwise wait
        if has_spot:
            # Optional: if last run on SPOT ended with a preemption, rotate region to diversify
            try:
                if (
                    last_cluster_type == ClusterType.SPOT
                    and getattr(self, "remaining_restart_overhead", 0.0) > 0.0
                ):
                    num_regions = getattr(self.env, "get_num_regions", lambda: 1)()
                    if num_regions and num_regions > 1:
                        cur_idx = self.env.get_current_region()
                        self.env.switch_region((cur_idx + 1) % num_regions)
            except Exception:
                # If env doesn't support region methods safely ignore
                pass
            return ClusterType.SPOT

        # No spot: wait to save cost until we must pivot (handled by lock above)
        # As a minor heuristic, rotate region during extended unavailability to search diversity
        try:
            if self._no_spot_consecutive >= 2:
                num_regions = getattr(self.env, "get_num_regions", lambda: 1)()
                if num_regions and num_regions > 1:
                    cur_idx = self.env.get_current_region()
                    self.env.switch_region((cur_idx + 1) % num_regions)
                    self._no_spot_consecutive = 0
        except Exception:
            pass

        return ClusterType.NONE