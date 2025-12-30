import json
from argparse import Namespace
from typing import List

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_multiregion_v1"

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
        self._committed_to_od = False
        self._num_regions = None
        self._last_true_ts: List[float] = []
        self._last_seen_ts: List[float] = []
        self._rr_next = 0

        # Efficient tracking of total work done to avoid summing each step
        self._last_task_done_len = 0
        self._sum_done_seconds = 0.0

        return self

    def _ensure_region_state(self):
        if self._num_regions is None:
            n = self.env.get_num_regions()
            self._num_regions = n
            self._last_true_ts = [-1.0] * n
            self._last_seen_ts = [-1.0] * n
            cur = self.env.get_current_region()
            self._rr_next = (cur + 1) % n

    def _update_progress_sum(self):
        # Efficiently update total done without O(N) each step
        cur_len = len(self.task_done_time)
        if cur_len > self._last_task_done_len:
            # Only add newly appended segments
            added = 0.0
            for v in self.task_done_time[self._last_task_done_len:cur_len]:
                added += float(v)
            self._sum_done_seconds += added
            self._last_task_done_len = cur_len

    def _remaining_work(self) -> float:
        self._update_progress_sum()
        remaining = self.task_duration - self._sum_done_seconds
        if remaining < 0.0:
            return 0.0
        return remaining

    def _safe_to_idle(self, t_left: float, remaining_work: float, gap: float) -> bool:
        # After idling one step, we must still be able to finish using OD (including one restart overhead).
        return (t_left - gap) >= (remaining_work + self.restart_overhead)

    def _should_commit_to_od_now(self, t_left: float, remaining_work: float) -> bool:
        # If time left is at or below OD time to finish including a potential restart overhead,
        # we must start OD now to guarantee completion.
        return t_left <= (remaining_work + self.restart_overhead)

    def _choose_next_region_to_try(self, current_region: int) -> int:
        # Choose region with most recent observed SPOT availability; fall back to simple round-robin.
        n = self._num_regions
        if n <= 1:
            return current_region

        # Prefer the most recently "True" region different from current
        best_region = -1
        best_ts = -1.0
        for r in range(n):
            if r == current_region:
                continue
            ts = self._last_true_ts[r]
            if ts > best_ts:
                best_ts = ts
                best_region = r

        if best_region >= 0 and best_ts >= 0.0:
            return best_region

        # Fallback: rotate
        nxt = self._rr_next
        if nxt == current_region:
            nxt = (nxt + 1) % n
        self._rr_next = (nxt + 1) % n
        return nxt

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_region_state()

        # If we are already on-demand, stick with it to avoid extra overheads and ensure finishing.
        if last_cluster_type == ClusterType.ON_DEMAND:
            self._committed_to_od = True

        now = float(self.env.elapsed_seconds)
        gap = float(self.env.gap_seconds)
        t_left = float(self.deadline - now)
        remaining_work = self._remaining_work()

        # Update observational stats for current region
        cur_region = self.env.get_current_region()
        self._last_seen_ts[cur_region] = now
        if has_spot:
            self._last_true_ts[cur_region] = now

        # If committed to OD, continue on-demand
        if self._committed_to_od:
            return ClusterType.ON_DEMAND

        # Decide whether to commit to OD now to guarantee completion
        if self._should_commit_to_od_now(t_left, remaining_work):
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        # If SPOT is available now, use it
        if has_spot:
            return ClusterType.SPOT

        # SPOT unavailable; decide whether to idle (search) or start OD
        if self._safe_to_idle(t_left, remaining_work, gap):
            # Try another region for next step (no cost to switch; overhead applies when we start)
            next_region = self._choose_next_region_to_try(cur_region)
            if next_region != cur_region:
                self.env.switch_region(next_region)
            return ClusterType.NONE

        # Not safe to idle anymore: commit to OD
        self._committed_to_od = True
        return ClusterType.ON_DEMAND