import json
from argparse import Namespace
from typing import List

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cbl_multi_sched_v1"

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
        self._initialized = False
        self._step_index = 0
        self._prev_region = None

        # Progress cache
        self._cached_done_len = 0
        self._cached_done_sum = 0.0

        # Region statistics (lazy init upon first _step when env is ready)
        self._region_avail: List[float] = []
        self._region_total: List[float] = []
        self._cooldown_until: List[int] = []
        self._backoff: List[int] = []

        return self

    # Helper: ensure region structures initialized
    def _ensure_init(self):
        if not self._initialized:
            try:
                n = self.env.get_num_regions()
            except Exception:
                # Fallback if get_num_regions not available: assume at least current region
                n = max(1, getattr(self.env, "num_regions", 1))
            self._region_avail = [1.0] * n  # prior
            self._region_total = [2.0] * n  # prior -> initial 0.5 ratio
            self._cooldown_until = [0] * n
            self._backoff = [0] * n
            self._prev_region = self.env.get_current_region()
            self._initialized = True

    def _update_region_stats(self, region: int, has_spot: bool):
        # Simple counting stats with priors already added
        self._region_total[region] += 1.0
        if has_spot:
            self._region_avail[region] += 1.0
            # Reset cooldown/backoff when available
            self._backoff[region] = 0
            self._cooldown_until[region] = 0
        else:
            # Increase backoff and set cooldown for a few steps
            self._backoff[region] = min(self._backoff[region] + 1, 6)
            self._cooldown_until[region] = self._step_index + min(4, self._backoff[region])

    def _choose_best_region(self, current_region: int) -> int:
        n = len(self._region_total)
        best_idx = None
        best_score = -1.0
        now_step = self._step_index
        for i in range(n):
            if i == current_region:
                continue
            if self._cooldown_until[i] > now_step:
                continue
            score = (self._region_avail[i]) / (self._region_total[i])
            if score > best_score:
                best_score = score
                best_idx = i
            elif score == best_score:
                # tie-breaker: prefer region with more observations
                if best_idx is None or self._region_total[i] > self._region_total[best_idx]:
                    best_idx = i
        if best_idx is None:
            # No eligible (due to cooldown); pick next cyclic
            best_idx = (current_region + 1) % n
        return best_idx

    def _get_work_done(self) -> float:
        # Efficient incremental sum of task_done_time
        lst = self.task_done_time
        n = len(lst)
        if n > self._cached_done_len:
            # Sum only new entries
            add_sum = 0.0
            for i in range(self._cached_done_len, n):
                add_sum += float(lst[i])
            self._cached_done_sum += add_sum
            self._cached_done_len = n
        return self._cached_done_sum

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_init()

        # Update region statistics based on current region and given spot availability
        current_region = self.env.get_current_region()
        self._update_region_stats(current_region, has_spot)

        # Compute remaining work
        work_done = self._get_work_done()
        remaining_work = max(0.0, self.task_duration - work_done)
        if remaining_work <= 0.0:
            self._prev_region = current_region
            self._step_index += 1
            return ClusterType.NONE

        gap = float(self.env.gap_seconds)
        now = float(self.env.elapsed_seconds)
        deadline = float(self.deadline)
        overhead = float(self.restart_overhead)

        # If already on on-demand, stick to it to avoid extra overheads and ensure deadline
        if last_cluster_type == ClusterType.ON_DEMAND:
            # Just continue OD until completion
            self._prev_region = current_region
            self._step_index += 1
            return ClusterType.ON_DEMAND

        # Compute slack relative to switching to On-Demand now (includes overhead)
        # If we're not currently on OD, we need to pay full restart_overhead when switching to OD.
        od_overhead_now = overhead
        slack = deadline - now - (remaining_work + od_overhead_now)

        # If spot is available in current region
        if has_spot:
            # If last step was SPOT and region unchanged, running spot now doesn't consume slack
            same_region_as_last = (self._prev_region == current_region)
            if last_cluster_type == ClusterType.SPOT and same_region_as_last:
                # Continue SPOT
                self._prev_region = current_region
                self._step_index += 1
                return ClusterType.SPOT
            else:
                # Starting SPOT now will consume 'overhead' worth of slack (since progress = gap - overhead)
                # Ensure we can afford that
                if slack >= overhead:
                    self._prev_region = current_region
                    self._step_index += 1
                    return ClusterType.SPOT
                else:
                    # Not enough slack to pay restart overhead for SPOT; switch to OD
                    self._prev_region = current_region
                    self._step_index += 1
                    return ClusterType.ON_DEMAND

        # Spot is unavailable in current region
        # If insufficient slack to wait for one step, go On-Demand
        if slack < 0.0:
            self._prev_region = current_region
            self._step_index += 1
            return ClusterType.ON_DEMAND

        # If we have at least one gap of slack, try searching other regions and pause this step
        if slack >= gap:
            # Switch to the best candidate region for the next step and wait
            next_region = self._choose_best_region(current_region)
            if next_region != current_region:
                self.env.switch_region(next_region)
            # After switching, set prev_region to new for this step (NONE runs in the new region)
            self._prev_region = self.env.get_current_region()
            self._step_index += 1
            return ClusterType.NONE

        # Not enough slack to wait for a full step; go On-Demand to guarantee finish
        self._prev_region = current_region
        self._step_index += 1
        return ClusterType.ON_DEMAND
