import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "robust_wait_rr"

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
        self._done_sum = 0.0
        self._done_len = 0
        self._initialized = False
        self._od_lock = False  # Once locked, stay on OD until task completes
        self._rr_next_region = 0
        self._last_region = None
        return self

    def _init_if_needed(self):
        if not self._initialized:
            self._initialized = True
            self._rr_next_region = self.env.get_current_region()
            self._last_region = self._rr_next_region

    def _update_done_sum(self):
        # Efficient incremental sum of task_done_time
        cur_len = len(self.task_done_time)
        if cur_len > self._done_len:
            # Sum the newly appended segments
            new_sum = 0.0
            for v in self.task_done_time[self._done_len:]:
                new_sum += v
            self._done_sum += new_sum
            self._done_len = cur_len

    def _safe_switch_region_round_robin(self):
        # Round robin to next region; do not switch to same index redundantly
        num_regions = self.env.get_num_regions()
        if num_regions <= 1:
            return
        next_idx = (self.env.get_current_region() + 1) % num_regions
        if next_idx != self.env.get_current_region():
            self.env.switch_region(next_idx)
        self._rr_next_region = next_idx
        self._last_region = next_idx

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._init_if_needed()
        self._update_done_sum()

        # Basic quantities
        gap = float(self.env.gap_seconds)
        O = float(self.restart_overhead)
        # Conservative buffer to handle discretization/overhead nuances
        fudge = O  # 1x restart overhead as extra buffer
        wait_margin = gap  # require at least one gap of extra slack to wait

        done = float(self._done_sum)
        total = float(self.task_duration)
        remaining_work = max(0.0, total - done)
        time_left = float(self.deadline - self.env.elapsed_seconds)

        if remaining_work <= 0.0:
            # Task complete
            return ClusterType.NONE

        # Slack S = time left - remaining work
        slack = time_left - remaining_work

        # Last-chance commitment: ensure we can always finish on OD
        # If we do not have enough slack beyond OD overhead, lock to OD
        if slack <= O + fudge:
            self._od_lock = True

        if self._od_lock:
            # Stay on on-demand to guarantee completion
            return ClusterType.ON_DEMAND

        # If Spot available and we are not locked, prefer Spot
        if has_spot:
            return ClusterType.SPOT

        # Spot not available now
        # Decide to wait (NONE) if we have sufficient slack; else use OD (bridging)
        if slack >= O + fudge + wait_margin:
            # Wait and try another region next step in a round-robin manner
            self._safe_switch_region_round_robin()
            return ClusterType.NONE
        else:
            # Use on-demand for now (bridging). Do not lock unless near deadline.
            # We already set lock above if slack is too tight.
            return ClusterType.ON_DEMAND