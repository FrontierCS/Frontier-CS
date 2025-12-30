import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
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

        # Internal state initialization
        self._work_done_cached = 0.0
        self._work_done_len = 0
        self._committed_od = False

        # Region stats for heuristic switching (EWMA)
        try:
            n_regions = self.env.get_num_regions()
        except Exception:
            n_regions = 1
        self._p_est = [0.5 for _ in range(n_regions)]
        self._ewma_alpha = 0.08

        # Waiting cycle counter (for optional behavior)
        self._wait_counter = 0

        return self

    def _update_work_done_cache(self):
        if hasattr(self, "task_done_time"):
            curr_len = len(self.task_done_time)
            if curr_len > self._work_done_len:
                # Sum only the new segments
                new_sum = 0.0
                for v in self.task_done_time[self._work_done_len:]:
                    new_sum += float(v)
                self._work_done_cached += new_sum
                self._work_done_len = curr_len

    def _safe_margin(self, time_left: float, rem_work: float, last_cluster_type: ClusterType) -> float:
        # Time needed on OD to finish if we commit now
        # Include one-time overhead if switching from non-OD to OD
        overhead_commit = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else float(self.restart_overhead)
        return time_left - (rem_work + overhead_commit)

    def _choose_region_when_waiting(self):
        # Simple round-robin to explore regions while waiting
        try:
            n = self.env.get_num_regions()
        except Exception:
            n = 1
        if n <= 1:
            return
        cur = self.env.get_current_region()
        next_idx = (cur + 1) % n
        if next_idx != cur:
            self.env.switch_region(next_idx)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update EWMA spot availability for current region
        try:
            cur_region = self.env.get_current_region()
            n_regions = self.env.get_num_regions()
            if len(self._p_est) != n_regions:
                # In case the environment changed number of regions unexpectedly
                self._p_est = [0.5 for _ in range(n_regions)]
            # EWMA update
            p_old = self._p_est[cur_region]
            self._p_est[cur_region] = p_old + self._ewma_alpha * ((1.0 if has_spot else 0.0) - p_old)
        except Exception:
            pass

        # Update cached sum of completed work
        self._update_work_done_cache()

        # Remaining work and time left
        rem_work = max(0.0, float(self.task_duration) - self._work_done_cached)
        time_left = float(self.deadline) - float(self.env.elapsed_seconds)
        gap = float(self.env.gap_seconds)
        overhead = float(self.restart_overhead)

        # If task finished, do nothing
        if rem_work <= 0.0:
            return ClusterType.NONE

        # If already committed to on-demand, stick to it
        if self._committed_od:
            return ClusterType.ON_DEMAND

        # If no time left or negative, still try ON_DEMAND
        if time_left <= 0.0:
            self._committed_od = True
            return ClusterType.ON_DEMAND

        # Compute safety margin relative to committing to OD now
        safe_margin = self._safe_margin(time_left, rem_work, last_cluster_type)

        # Define guard thresholds
        # If we try one more SPOT step and it fails, we still want to be able to finish on OD.
        guard_spot = gap + overhead  # conservative single-step guard
        # For waiting (NONE) when spot is not available, allow at most one step of waiting slack
        wait_guard = gap + overhead

        # Decision logic
        if has_spot:
            # If margin is too thin, commit to OD to avoid risk near deadline
            if safe_margin <= guard_spot:
                self._committed_od = True
                return ClusterType.ON_DEMAND
            # Otherwise, use spot
            self._wait_counter = 0
            return ClusterType.SPOT
        else:
            # Spot not available here: wait if we have slack, otherwise commit to OD
            if safe_margin > wait_guard:
                # We can safely wait and try other regions
                self._wait_counter += 1
                self._choose_region_when_waiting()
                return ClusterType.NONE
            else:
                # Not enough slack to wait, commit to OD
                self._committed_od = True
                self._wait_counter = 0
                return ClusterType.ON_DEMAND