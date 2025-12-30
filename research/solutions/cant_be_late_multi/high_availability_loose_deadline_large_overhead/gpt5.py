import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_mr"

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
        self._committed_to_od = False
        self._done_acc = 0.0
        self._last_done_len = 0
        self._rr_initialized = False
        self._rr_next_region = 0
        return self

    def _init_rr(self):
        if not self._rr_initialized:
            try:
                n = self.env.get_num_regions()
            except Exception:
                n = 1
            if n <= 0:
                n = 1
            try:
                cur = self.env.get_current_region()
            except Exception:
                cur = 0
            self._rr_next_region = (cur + 1) % n
            self._rr_initialized = True

    def _update_done_acc(self):
        # Incremental sum of task_done_time to avoid O(n) sum per step
        tlist = self.task_done_time
        if tlist is None:
            return
        if len(tlist) > self._last_done_len:
            # Typically only 0 or 1 new segment per step
            for i in range(self._last_done_len, len(tlist)):
                self._done_acc += tlist[i]
            self._last_done_len = len(tlist)

    def _get_remaining_work(self):
        self._update_done_acc()
        remaining = self.task_duration - self._done_acc
        if remaining < 0.0:
            remaining = 0.0
        return remaining

    def _time_left(self):
        tl = self.deadline - self.env.elapsed_seconds
        if tl < 0.0:
            tl = 0.0
        return tl

    def _next_region_rr(self):
        self._init_rr()
        try:
            n = self.env.get_num_regions()
        except Exception:
            n = 1
        if n <= 1:
            return self.env.get_current_region() if hasattr(self.env, "get_current_region") else 0
        nxt = self._rr_next_region
        self._rr_next_region = (nxt + 1) % n
        return nxt

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Ensure round-robin state initialized
        self._init_rr()

        # If already committed to on-demand, keep running OD
        if self._committed_to_od:
            return ClusterType.ON_DEMAND

        # Compute remaining work and time
        rem_work = self._get_remaining_work()
        if rem_work <= 0.0:
            return ClusterType.NONE
        time_left = self._time_left()
        if time_left <= 0.0:
            # Out of time; return NONE to avoid errors
            return ClusterType.NONE

        step = self.env.gap_seconds
        overhead = self.restart_overhead

        # Slack is extra wall time beyond required work
        slack = time_left - rem_work

        # If slack is at or below overhead, we must commit to OD now to guarantee finish
        if slack <= overhead:
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        # If spot is available, use it to minimize cost
        if has_spot:
            return ClusterType.SPOT

        # Spot unavailable:
        # Decide whether it's safe to wait one step (NONE) while switching region, or commit to OD now.
        # It's safe to wait if after wasting one step, we still have at least overhead slack.
        # i.e., (time_left - step) - rem_work >= overhead  => slack - step >= overhead
        if slack - step >= overhead:
            # Wait and try another region next step
            try:
                nxt = self._next_region_rr()
                curr = self.env.get_current_region()
                if nxt != curr:
                    self.env.switch_region(nxt)
            except Exception:
                pass
            return ClusterType.NONE

        # Not safe to wait; commit to OD now
        self._committed_to_od = True
        return ClusterType.ON_DEMAND