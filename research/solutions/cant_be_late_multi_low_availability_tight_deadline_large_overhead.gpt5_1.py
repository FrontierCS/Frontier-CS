import json
from argparse import Namespace
from typing import List, Optional

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_mr_budget_v2"

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

        # Strategy state initialization
        self._initialized = False
        self._done_sum_cache = 0.0
        self._done_len_cache = 0
        self._committed_to_od = False
        self._region_stats = []
        self._region_last_good: List[float] = []
        self._last_rotate_at = -1.0
        self._rotate_index = 0
        self._last_region = None
        return self

    def _init_runtime(self):
        if self._initialized:
            return
        self._initialized = True
        try:
            num_regions = self.env.get_num_regions()
        except Exception:
            num_regions = 1
        self._num_regions = max(1, int(num_regions))
        try:
            current_region = self.env.get_current_region()
        except Exception:
            current_region = 0
        self._rotate_index = current_region if 0 <= current_region < self._num_regions else 0
        self._last_region = current_region
        self._region_stats = [{'success': 0, 'fail': 0} for _ in range(self._num_regions)]
        self._region_last_good = [-1.0 for _ in range(self._num_regions)]
        self._gap = float(getattr(self.env, 'gap_seconds', 1.0))
        # Small buffer to avoid tight edge at deadline; tuned for safety without being too aggressive
        self._base_buffer = max(30.0, min(self._gap * 1.0, self.restart_overhead * 0.5))

    def _update_done_cache(self):
        if self._done_len_cache != len(self.task_done_time):
            for i in range(self._done_len_cache, len(self.task_done_time)):
                self._done_sum_cache += float(self.task_done_time[i])
            self._done_len_cache = len(self.task_done_time)

    def _remaining_work(self) -> float:
        self._update_done_cache()
        remaining = self.task_duration - self._done_sum_cache
        return max(0.0, remaining)

    def _remaining_time(self) -> float:
        return max(0.0, self.deadline - float(self.env.elapsed_seconds))

    def _choose_next_region(self, current_region: int) -> int:
        # If only one region, do not switch
        if self._num_regions <= 1:
            return current_region

        # Prefer region with most recent success, else simple round-robin
        # Time window weight is small; this is a heuristic
        now = float(self.env.elapsed_seconds)
        best_region = current_region
        best_time = -1.0
        for idx in range(self._num_regions):
            last_good = self._region_last_good[idx]
            if last_good > best_time and idx != current_region:
                best_time = last_good
                best_region = idx

        # If no region has any recent success recorded, rotate round-robin
        if best_time < 0:
            nxt = (current_region + 1) % self._num_regions
            return nxt
        return best_region

    def _commit_check(self) -> bool:
        # Decide to permanently switch to On-Demand to guarantee completion
        remaining_work = self._remaining_work()
        remaining_time = self._remaining_time()
        # We need at least (overhead + remaining_work + buffer) seconds to safely finish on OD.
        needed = self.restart_overhead + remaining_work + self._base_buffer
        return remaining_time <= needed

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._init_runtime()

        # Update region stats based on current has_spot observation
        try:
            current_region = self.env.get_current_region()
        except Exception:
            current_region = 0
        self._last_region = current_region

        if has_spot:
            self._region_stats[current_region]['success'] += 1
            self._region_last_good[current_region] = float(self.env.elapsed_seconds)
        else:
            self._region_stats[current_region]['fail'] += 1

        # If already committed to OD, keep using OD to avoid additional overheads and risks.
        if self._committed_to_od:
            return ClusterType.ON_DEMAND

        # If we must commit now to ensure finishing before deadline
        if self._commit_check():
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        # If Spot is available, use it.
        if has_spot:
            return ClusterType.SPOT

        # Spot not available and we still have slack: pause and switch region to hunt for spot next step.
        next_region = self._choose_next_region(current_region)
        if next_region != current_region:
            try:
                self.env.switch_region(next_region)
                self._last_rotate_at = float(self.env.elapsed_seconds)
                self._rotate_index = next_region
            except Exception:
                # If switch fails for any reason, just continue without switching
                pass

        # Wait for spot; no cost while we have slack
        return ClusterType.NONE
