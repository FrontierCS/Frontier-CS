import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_mr_v1"

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
        self._commit_on_demand = False
        self._work_done_sum = 0.0
        self._work_done_count = 0
        self._last_spot_true_time = None
        self._finish_safety = None
        self._rr_index = 0
        self._num_regions_cached = None
        return self

    def _initialize_if_needed(self):
        if self._initialized:
            return
        # Cache number of regions and initialize tracking arrays
        try:
            n = self.env.get_num_regions()
        except Exception:
            n = 1
        if n is None or n <= 0:
            n = 1
        self._num_regions_cached = n
        self._last_spot_true_time = [-1.0] * n
        try:
            self._rr_index = int(self.env.get_current_region()) % n
        except Exception:
            self._rr_index = 0
        # Safety margin to ensure finishing before deadline (seconds)
        # Use twice the restart overhead as a conservative buffer.
        self._finish_safety = max(self.restart_overhead * 2.0, 0.0)
        self._initialized = True

    def _update_work_done_cache(self):
        # Incrementally sum newly appended segments to avoid O(n) per step
        lst = self.task_done_time
        if lst is None:
            return
        try:
            cur_len = len(lst)
        except Exception:
            # Fallback to direct sum in rare unexpected cases
            try:
                self._work_done_sum = float(sum(lst))
                self._work_done_count = len(lst)
            except Exception:
                pass
            return
        if cur_len < self._work_done_count:
            # List unexpectedly shrank; fallback to full resync
            self._work_done_sum = float(sum(lst))
            self._work_done_count = cur_len
            return
        if cur_len > self._work_done_count:
            # Sum tail only
            try:
                add_sum = float(sum(lst[self._work_done_count:]))
            except Exception:
                # Fallback: full sum
                self._work_done_sum = float(sum(lst))
                self._work_done_count = cur_len
                return
            self._work_done_sum += add_sum
            self._work_done_count = cur_len

    def _best_next_region(self, current_region: int) -> int:
        n = self._num_regions_cached if self._num_regions_cached else 1
        if n <= 1:
            return current_region
        # Prefer region with latest recent spot availability; fallback to round-robin
        best_idx = -1
        best_time = -1.0
        times = self._last_spot_true_time
        # Find best region not equal to current
        for i in range(n):
            if i == current_region:
                continue
            t = times[i]
            if t > best_time:
                best_time = t
                best_idx = i
        if best_idx >= 0 and best_time >= 0.0:
            return best_idx
        # Fallback to round-robin
        self._rr_index = (self._rr_index + 1) % n
        if self._rr_index == current_region:
            self._rr_index = (self._rr_index + 1) % n
        return self._rr_index

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._initialize_if_needed()

        # Update observed spot info for current region
        try:
            current_region = int(self.env.get_current_region())
        except Exception:
            current_region = 0
        if 0 <= current_region < (self._num_regions_cached or 1):
            if has_spot:
                # Record last time spot was available in this region
                try:
                    self._last_spot_true_time[current_region] = float(self.env.elapsed_seconds)
                except Exception:
                    pass

        # Update cached work done
        self._update_work_done_cache()

        # Remaining work and time left
        work_remaining = max(float(self.task_duration) - float(self._work_done_sum), 0.0)
        time_left = float(self.deadline) - float(self.env.elapsed_seconds)

        if work_remaining <= 0.0:
            # Done; no cluster needed
            return ClusterType.NONE

        # Determine overhead if we switch to on-demand now
        overhead_to_on_demand = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else float(self.restart_overhead)

        # If already committed to on-demand, keep using it to avoid extra overheads
        if self._commit_on_demand:
            return ClusterType.ON_DEMAND

        # Urgency check: must ensure completion before deadline
        if time_left <= work_remaining + overhead_to_on_demand + self._finish_safety:
            self._commit_on_demand = True
            return ClusterType.ON_DEMAND

        # Prefer spot when available and we're not committed to on-demand
        if has_spot:
            return ClusterType.SPOT

        # Spot not available: decide to wait (NONE) and possibly scan another region,
        # if we can afford to wait for one step and still complete on-demand.
        gap = float(self.env.gap_seconds)
        if time_left - gap > work_remaining + overhead_to_on_demand + self._finish_safety:
            # We can wait one step safely; switch to a promising region to probe next step
            try:
                next_region = self._best_next_region(current_region)
                if next_region != current_region:
                    self.env.switch_region(next_region)
            except Exception:
                pass
            return ClusterType.NONE

        # Not enough slack to wait; commit to on-demand now
        self._commit_on_demand = True
        return ClusterType.ON_DEMAND