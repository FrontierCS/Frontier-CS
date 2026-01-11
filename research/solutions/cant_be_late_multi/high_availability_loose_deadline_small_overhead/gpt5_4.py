import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cbl_rr_guard_v1"

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
        self._commit_od = False
        self._n_regions = None
        self._rr_next = 0
        self._last_done_len = 0
        self._done_sum = 0.0

        # Initialize region info if env is ready
        try:
            self._n_regions = self.env.get_num_regions()
            cur = self.env.get_current_region()
            if self._n_regions and self._n_regions > 0:
                self._rr_next = (cur + 1) % self._n_regions
        except Exception:
            pass

        return self

    def _ensure_state_init(self):
        if self._n_regions is None:
            try:
                self._n_regions = self.env.get_num_regions()
                cur = self.env.get_current_region()
                if self._n_regions and self._n_regions > 0:
                    self._rr_next = (cur + 1) % self._n_regions
                else:
                    self._n_regions = 1
                    self._rr_next = 0
            except Exception:
                self._n_regions = 1
                self._rr_next = 0

    def _update_done_sum(self):
        l = len(self.task_done_time)
        if l > self._last_done_len:
            # Incrementally update to avoid O(n^2)
            inc = 0.0
            for v in self.task_done_time[self._last_done_len:]:
                inc += v
            self._done_sum += inc
            self._last_done_len = l

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_state_init()
        self._update_done_sum()

        # Quick completion check
        remaining_work = self.task_duration - self._done_sum
        if remaining_work <= 0:
            return ClusterType.NONE

        gap = float(self.env.gap_seconds)
        rem_time = float(self.deadline - self.env.elapsed_seconds)
        overhead = float(self.restart_overhead)

        # If already on on-demand, stick to it to avoid extra overhead/risk
        if self._commit_od or last_cluster_type == ClusterType.ON_DEMAND:
            self._commit_od = True
            return ClusterType.ON_DEMAND

        # Time buffer if we switch to on-demand now (one-time overhead + remaining work)
        od_switch_overhead = overhead
        extra_time = rem_time - (remaining_work + od_switch_overhead)

        # Guard threshold: ensure we can lose at least one step and still finish on OD
        guard = gap

        # Decide action
        if has_spot:
            if extra_time >= guard:
                return ClusterType.SPOT
            else:
                self._commit_od = True
                return ClusterType.ON_DEMAND
        else:
            if extra_time >= guard:
                # Wait this step and try another region next step
                if self._n_regions and self._n_regions > 1:
                    current = self.env.get_current_region()
                    nxt = self._rr_next
                    if nxt == current:
                        nxt = (current + 1) % self._n_regions
                    self.env.switch_region(nxt)
                    self._rr_next = (nxt + 1) % self._n_regions
                return ClusterType.NONE
            else:
                self._commit_od = True
                return ClusterType.ON_DEMAND