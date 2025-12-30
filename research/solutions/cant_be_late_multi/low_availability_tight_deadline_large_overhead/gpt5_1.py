import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_v1"

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
        # Internal state (initialized on first _step call)
        self._initialized = False
        return self

    def _init_run_state(self):
        # Called at the beginning of each scenario/run
        self._initialized = True
        self._progress_sum = 0.0
        self._progress_len = 0
        self._last_elapsed = self.env.elapsed_seconds
        self._committed_to_od = False
        # Round-robin region rotation pointer
        try:
            cur = self.env.get_current_region()
        except Exception:
            cur = 0
        self._rr_next_region = cur
        self._last_region = cur

    def _update_progress_sum(self):
        # Incremental update to avoid O(n) sum at each step
        if self._progress_len < len(self.task_done_time):
            # Sum only new entries
            new_items = self.task_done_time[self._progress_len :]
            if new_items:
                self._progress_sum += float(sum(new_items))
                self._progress_len = len(self.task_done_time)

    def _maybe_reset_state(self):
        # Detect new run by elapsed time going backwards or zero with empty progress
        if not self._initialized:
            self._init_run_state()
            return
        if self.env.elapsed_seconds < self._last_elapsed:
            self._init_run_state()

    def _safe_to_wait_one_step(self, time_left, remaining, extra_margin):
        # Check if it's safe to spend one step waiting (NONE) and still be able to
        # finish on OD afterwards (including one restart overhead).
        # After waiting one step, time_left' = time_left - gap_seconds
        # We require: time_left - gap_seconds >= remaining + restart_overhead + extra_margin
        return (time_left - self.env.gap_seconds) >= (remaining + self.restart_overhead + extra_margin)

    def _commit_needed(self, time_left, remaining, extra_margin):
        # Commit to OD if time left is tight relative to remaining work
        # Condition: time_left <= remaining + restart_overhead + extra_margin
        return time_left <= (remaining + self.restart_overhead + extra_margin)

    def _rotate_region_on_wait(self):
        # Rotate to next region in round-robin order when waiting for Spot
        try:
            n = self.env.get_num_regions()
        except Exception:
            n = 1
        if n <= 1:
            return  # Nothing to do
        cur = self.env.get_current_region()
        # Initialize next pointer if out of range
        if not isinstance(self._rr_next_region, int) or not (0 <= self._rr_next_region < n):
            self._rr_next_region = cur

        # Choose next different region
        nxt = (cur + 1) % n
        if nxt == cur:
            return
        self.env.switch_region(nxt)
        self._rr_next_region = (nxt + 1) % n
        self._last_region = nxt

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._maybe_reset_state()

        # Maintain incremental progress sum
        self._update_progress_sum()

        # Cache elapsed for next reset detection
        self._last_elapsed = self.env.elapsed_seconds

        # Compute remaining work and time left
        remaining = max(self.task_duration - self._progress_sum, 0.0)
        time_left = max(self.deadline - self.env.elapsed_seconds, 0.0)

        # If job already done (safety)
        if remaining <= 0.0:
            return ClusterType.NONE

        # Safety extra margins
        # Commit buffer encourages earlier switch to OD to guarantee finish.
        # We use one gap as buffer to cover discrete steps plus a small extra.
        commit_extra_margin = self.env.gap_seconds * 1.0
        wait_extra_margin = self.env.gap_seconds * 0.2

        # If already committed to OD, keep using OD until finish
        if self._committed_to_od:
            return ClusterType.ON_DEMAND

        # Decide if we should commit to OD right now
        # Even if spot is available, if the remaining time is tight, commit to OD to guarantee finish.
        if self._commit_needed(time_left, remaining, commit_extra_margin):
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        # If Spot is available, use it to save cost
        if has_spot:
            return ClusterType.SPOT

        # Spot not available: decide whether to wait for spot (NONE) or commit to OD
        # If it's not safe to wait one step and still finish on OD, commit now
        if not self._safe_to_wait_one_step(time_left, remaining, wait_extra_margin):
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        # Safe to wait; rotate region to try another spot market
        self._rotate_region_on_wait()
        return ClusterType.NONE