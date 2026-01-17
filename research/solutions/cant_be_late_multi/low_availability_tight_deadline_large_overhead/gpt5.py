import json
import math
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cbl_lazy_rr_v3"

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
        self._initialized = False
        self._committed_od = False
        self._region_scores = None
        self._alpha = 0.2
        self._no_spot_streak = 0
        return self

    def _initialize_if_needed(self):
        if not self._initialized:
            try:
                n = int(self.env.get_num_regions())
            except Exception:
                n = 1
            self._num_regions = max(1, n)
            self._region_scores = [0.5] * self._num_regions
            self._initialized = True

    def _time_needed_on_demand(self, remaining_work: float) -> float:
        # Exact discrete-step time needed to finish if we switch to On-Demand now and stay on it
        g = float(self.env.gap_seconds)
        r = float(self.restart_overhead)
        if remaining_work <= 0:
            return 0.0
        if g <= 0:
            # Fallback: continuous approximation
            return r + remaining_work
        h_steps = int(math.ceil(r / g)) if r > 0 else 0
        progress_during_overhead_steps = max(0.0, g * h_steps - r)
        remaining_after = max(0.0, remaining_work - progress_during_overhead_steps)
        w_steps = int(math.ceil(remaining_after / g)) if remaining_after > 0 else 0
        return (h_steps + w_steps) * g

    def _pick_region_when_no_spot(self, current_region: int) -> int:
        # Choose region with highest score; if tie, prefer next regions cyclically
        n = self._num_regions
        best_idx = current_region
        best_score = self._region_scores[current_region]
        for k in range(1, n + 1):
            j = (current_region + k) % n
            sc = self._region_scores[j]
            if sc > best_score + 1e-12:
                best_score = sc
                best_idx = j
        if best_idx == current_region and n > 1:
            best_idx = (current_region + 1) % n
        return best_idx

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._initialize_if_needed()

        # Update region score with current observation
        cur_region = self.env.get_current_region()
        if 0 <= cur_region < self._num_regions:
            s = 1.0 if has_spot else 0.0
            self._region_scores[cur_region] = (1.0 - self._alpha) * self._region_scores[cur_region] + self._alpha * s

        # Compute timing
        elapsed = float(self.env.elapsed_seconds)
        time_left = max(0.0, float(self.deadline) - elapsed)
        completed = float(sum(self.task_done_time))
        remaining_work = max(0.0, float(self.task_duration) - completed)

        # If done, stop
        if remaining_work <= 1e-9:
            return ClusterType.NONE

        # If already committed to On-Demand, keep using it
        if self._committed_od:
            return ClusterType.ON_DEMAND

        # Determine if we must commit to On-Demand now to safely meet deadline
        time_needed_od_now = self._time_needed_on_demand(remaining_work)
        preemption_safety_buffer = float(self.restart_overhead)  # cover potential one more overhead if we risk spot
        if time_left <= time_needed_od_now + preemption_safety_buffer:
            self._committed_od = True
            return ClusterType.ON_DEMAND

        # Spot-hunt mode
        if has_spot:
            self._no_spot_streak = 0
            return ClusterType.SPOT

        # No spot available: wait (NONE) and optionally switch region to improve chances next step
        self._no_spot_streak += 1
        if self._num_regions > 1:
            best_region = self._pick_region_when_no_spot(cur_region)
            if best_region != cur_region:
                self.env.switch_region(best_region)
        return ClusterType.NONE