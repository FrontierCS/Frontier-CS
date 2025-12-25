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
        # Internal state init
        self._inited = False
        self._commit_to_od = False
        self._accum_work = 0.0
        self._last_tdt_len = 0
        return self

    def _init_internal(self):
        if self._inited:
            return
        n = self.env.get_num_regions()
        self._num_regions = n
        self._region_score = [0.5 for _ in range(n)]  # EWMA of availability
        self._region_seen = [0 for _ in range(n)]
        self._streak_up = [0 for _ in range(n)]
        self._streak_down = [0 for _ in range(n)]
        # Tuning
        self._alpha = 0.05  # EWMA update rate
        self._switch_thresh = 0.05  # minimum improvement to switch
        self._streak_norm = 3  # hours normalization for streak bonus
        # Safety margin to ensure OD fallback time
        dt = self.env.gap_seconds
        self._safety_margin = min(0.5 * dt, 1.5 * self.restart_overhead)
        self._inited = True

    def _update_progress(self):
        # Incrementally sum task_done_time to avoid O(n^2)
        if self._last_tdt_len < len(self.task_done_time):
            new_seg = self.task_done_time[self._last_tdt_len :]
            self._accum_work += sum(new_seg)
            self._last_tdt_len = len(self.task_done_time)

    def _best_region(self, current_idx: int):
        # Score = EWMA + small bonus for consecutive availability
        best_idx = current_idx
        best_score = -1.0
        for i in range(self._num_regions):
            streak_bonus = 0.03 * min(self._streak_up[i] / max(self._streak_norm, 1), 1.0)
            score = self._region_score[i] + streak_bonus
            if score > best_score:
                best_score = score
                best_idx = i
        return best_idx, best_score

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._init_internal()
        self._update_progress()

        # Basic quantities
        dt = self.env.gap_seconds
        time_elapsed = self.env.elapsed_seconds
        time_left = self.deadline - time_elapsed
        work_done = self._accum_work
        remaining_work = max(0.0, self.task_duration - work_done)

        # Update region statistics with current observation
        cur_region = self.env.get_current_region()
        obs = 1.0 if has_spot else 0.0
        # EWMA update
        self._region_score[cur_region] = (
            (1.0 - self._alpha) * self._region_score[cur_region] + self._alpha * obs
        )
        self._region_seen[cur_region] += 1
        if has_spot:
            self._streak_up[cur_region] += 1
            self._streak_down[cur_region] = 0
        else:
            self._streak_down[cur_region] += 1
            self._streak_up[cur_region] = 0

        # Compute slack (time that can be wasted) with one OD restart overhead reserved
        slack = time_left - (remaining_work + self.restart_overhead)

        # Decide if we must commit to OD to finish before deadline
        if not self._commit_to_od and slack <= self._safety_margin:
            self._commit_to_od = True

        # If committed to OD, always run OD to finish
        if self._commit_to_od:
            return ClusterType.ON_DEMAND

        # If Spot available, always use it (cheap + progress)
        if has_spot:
            return ClusterType.SPOT

        # Spot not available and not committed to OD: wait (NONE) and try better region
        # Choose best region by historical availability score
        best_idx, best_score = self._best_region(cur_region)
        current_score = self._region_score[cur_region]
        # Switch if there is a meaningful improvement or current looks bad
        if best_idx != cur_region:
            if best_score - current_score >= self._switch_thresh or current_score < 0.35:
                self.env.switch_region(best_idx)

        return ClusterType.NONE
