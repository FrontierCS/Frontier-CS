import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cantbelate_scanner_v1"

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
        # Runtime state (initialized lazily in _step)
        self._initialized = False
        self._commit_od = False
        self._region_scores = None
        self._rr_ptr = 0
        self._alpha = 0.08  # EWMA smoothing for spot availability per region
        return self

    def _init_runtime(self):
        if self._initialized:
            return
        try:
            num_regions = self.env.get_num_regions()
        except Exception:
            num_regions = 1
        self._region_scores = [0.5] * max(1, num_regions)
        self._rr_ptr = 0
        self._initialized = True

    def _sum_done(self):
        # Sum of completed useful work (seconds)
        return sum(self.task_done_time) if self.task_done_time else 0.0

    def _remaining_work(self):
        return max(0.0, self.task_duration - self._sum_done())

    def _time_left(self):
        return self.deadline - self.env.elapsed_seconds

    def _overhead_if_switch_to_od(self, last_cluster_type: ClusterType):
        # If we are already committed or running on OD, no additional overhead
        if last_cluster_type == ClusterType.ON_DEMAND or self._commit_od:
            return 0.0
        return self.restart_overhead

    def _safety_buffer(self):
        # Add a small safety buffer to account for discretization and control delays
        gap = getattr(self.env, "gap_seconds", 60.0)
        return max(10.0, min(600.0, 0.25 * gap))

    def _update_region_score(self, region_idx: int, has_spot: bool):
        if region_idx is None or region_idx < 0 or region_idx >= len(self._region_scores):
            return
        p_old = self._region_scores[region_idx]
        obs = 1.0 if has_spot else 0.0
        alpha = self._alpha
        self._region_scores[region_idx] = (1.0 - alpha) * p_old + alpha * obs

    def _best_region_by_score(self):
        best_idx = 0
        best_score = self._region_scores[0]
        for i in range(1, len(self._region_scores)):
            s = self._region_scores[i]
            if s > best_score:
                best_score = s
                best_idx = i
        return best_idx, best_score

    def _pick_idle_region(self, current_region: int):
        # Choose region with highest score; if tie within 0.02, round-robin for exploration
        best_idx, best_score = self._best_region_by_score()
        cur_score = self._region_scores[current_region]
        # Tolerance for tie
        tol = 0.02
        if best_score - cur_score <= tol:
            # Explore via round-robin to avoid sticking to one region with similar score
            self._rr_ptr = (self._rr_ptr + 1) % len(self._region_scores)
            return self._rr_ptr
        return best_idx

    def _must_switch_to_od(self, last_cluster_type: ClusterType):
        # Decide if we must switch to OD now to guarantee finishing before deadline
        remaining = self._remaining_work()
        time_left = self._time_left()
        # If already finished, no need to switch
        if remaining <= 0.0:
            return False
        needed = remaining + self._overhead_if_switch_to_od(last_cluster_type) + self._safety_buffer()
        return time_left <= needed

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._init_runtime()

        # Update per-region spot availability score
        try:
            cur_region = self.env.get_current_region()
        except Exception:
            cur_region = 0
        self._update_region_score(cur_region, has_spot)

        # If already committed to OD or currently running OD, keep OD to ensure completion
        if last_cluster_type == ClusterType.ON_DEMAND:
            self._commit_od = True

        remaining = self._remaining_work()
        if remaining <= 0.0:
            return ClusterType.NONE

        # Hard-deadline safeguard: if we must switch to OD now, do it
        if not self._commit_od and self._must_switch_to_od(last_cluster_type):
            self._commit_od = True
            return ClusterType.ON_DEMAND

        if self._commit_od:
            return ClusterType.ON_DEMAND

        # Use SPOT when available and we are not in the danger zone
        if has_spot:
            return ClusterType.SPOT

        # Spot is unavailable in current region; wait if we still have slack, possibly switch region to seek availability
        # If we are close to danger zone (within a buffer), switch to OD
        time_left = self._time_left()
        needed_if_od_now = remaining + self._overhead_if_switch_to_od(last_cluster_type) + self._safety_buffer()
        if time_left <= needed_if_od_now:
            self._commit_od = True
            return ClusterType.ON_DEMAND

        # Otherwise, pause to save cost and try another region with better estimated availability
        if len(self._region_scores) > 1:
            target_region = self._pick_idle_region(cur_region)
            if target_region != cur_region:
                try:
                    self.env.switch_region(target_region)
                except Exception:
                    pass
        return ClusterType.NONE