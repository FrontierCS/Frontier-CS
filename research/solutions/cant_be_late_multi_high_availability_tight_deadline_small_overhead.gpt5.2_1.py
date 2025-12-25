import json
from argparse import Namespace
from typing import Optional, List

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


_CT_NONE = getattr(ClusterType, "NONE", getattr(ClusterType, "None", None))


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

        self._inited = False
        self._gap = None
        self._num_regions = None

        self._work_done = 0.0
        self._last_task_done_len = 0

        self._last_elapsed = None
        self._last_work_done_for_ema = 0.0
        self._ema_prod = 0.95
        self._ema_alpha = 0.02

        self._last_region = None
        self._consec_spot = 0
        self._consec_no_spot = 0

        self._commit_on_demand = False

        self._search_active = False
        self._search_order = []
        self._search_pos = 0
        self._next_probe_time = 0.0
        self._probe_interval = 30.0

        self._spot_seen = []
        self._seen_total = []
        self._perm_regions = []

        self._config = config
        return self

    def _lazy_init(self) -> None:
        if self._inited:
            return
        self._gap = float(getattr(self.env, "gap_seconds", 1.0))
        self._num_regions = int(self.env.get_num_regions())
        self._probe_interval = max(5.0 * self._gap, 30.0)

        self._spot_seen = [0] * self._num_regions
        self._seen_total = [0] * self._num_regions
        self._perm_regions = list(range(self._num_regions))
        self._inited = True

    def _update_work_done(self) -> None:
        l = len(self.task_done_time)
        if l > self._last_task_done_len:
            self._work_done += sum(self.task_done_time[self._last_task_done_len:l])
            self._last_task_done_len = l

    def _update_ema_prod(self, elapsed: float) -> None:
        if self._last_elapsed is None:
            self._last_elapsed = elapsed
            self._last_work_done_for_ema = self._work_done
            return
        dt = elapsed - self._last_elapsed
        if dt <= 0:
            return
        dw = self._work_done - self._last_work_done_for_ema
        inst = max(0.0, min(1.0, dw / dt))
        self._ema_prod = (1.0 - self._ema_alpha) * self._ema_prod + self._ema_alpha * inst
        self._last_elapsed = elapsed
        self._last_work_done_for_ema = self._work_done

    def _start_search(self, cur_region: int, elapsed: float) -> None:
        self._search_active = True
        if self._num_regions <= 1:
            self._search_order = []
            self._search_pos = 0
            self._next_probe_time = elapsed + self._probe_interval
            return
        self._search_order = [r for r in self._perm_regions if r != cur_region]
        self._search_pos = 0
        self._next_probe_time = elapsed

    def _best_region_by_history(self) -> int:
        best_r = 0
        best_score = -1.0
        for r in range(self._num_regions):
            total = self._seen_total[r]
            hits = self._spot_seen[r]
            score = (hits + 1.0) / (total + 2.0)
            if score > best_score:
                best_score = score
                best_r = r
        return best_r

    def _maybe_switch_to_next_search_region(self) -> None:
        if self._search_pos < len(self._search_order):
            nxt = self._search_order[self._search_pos]
            self._search_pos += 1
            self.env.switch_region(nxt)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._lazy_init()

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0))
        cur_region = int(self.env.get_current_region())
        if self._last_region is None or cur_region != self._last_region:
            self._consec_spot = 0
            self._consec_no_spot = 0
            self._last_region = cur_region

        self._seen_total[cur_region] += 1
        if has_spot:
            self._spot_seen[cur_region] += 1

        self._update_work_done()
        self._update_ema_prod(elapsed)

        remaining_work = float(self.task_duration) - float(self._work_done)
        if remaining_work <= 0.0:
            return _CT_NONE

        time_left = float(self.deadline) - elapsed
        if time_left <= 0.0:
            return _CT_NONE

        if has_spot:
            self._consec_spot += 1
            self._consec_no_spot = 0
        else:
            self._consec_no_spot += 1
            self._consec_spot = 0

        full_overhead = float(self.restart_overhead)
        rem_overhead = float(getattr(self, "remaining_restart_overhead", 0.0))

        if last_cluster_type == ClusterType.ON_DEMAND:
            need_if_od_now = remaining_work + max(0.0, rem_overhead)
        else:
            need_if_od_now = remaining_work + full_overhead

        critical_margin = 5.0 * self._gap
        if need_if_od_now >= time_left - critical_margin:
            self._commit_on_demand = True

        if self._commit_on_demand:
            self._search_active = False
            return ClusterType.ON_DEMAND

        if rem_overhead > 0.0:
            if last_cluster_type == ClusterType.ON_DEMAND:
                self._search_active = False
                return ClusterType.ON_DEMAND
            if last_cluster_type == ClusterType.SPOT and has_spot:
                self._search_active = False
                return ClusterType.SPOT

        slack = time_left - remaining_work

        if has_spot:
            self._search_active = False
            if last_cluster_type == ClusterType.ON_DEMAND:
                if slack > full_overhead + 600.0 and self._consec_spot >= 5:
                    return ClusterType.SPOT
                return ClusterType.ON_DEMAND
            return ClusterType.SPOT

        if last_cluster_type == ClusterType.ON_DEMAND:
            if slack > full_overhead + 1800.0:
                self._start_search(cur_region, elapsed)
                self._maybe_switch_to_next_search_region()
                return _CT_NONE
            return ClusterType.ON_DEMAND

        if not self._search_active:
            if slack > full_overhead + 600.0:
                self._start_search(cur_region, elapsed)
                self._maybe_switch_to_next_search_region()
                return _CT_NONE
            return ClusterType.ON_DEMAND if slack < full_overhead + 300.0 else _CT_NONE

        if elapsed < self._next_probe_time:
            return _CT_NONE

        if self._num_regions <= 1:
            self._next_probe_time = elapsed + self._probe_interval
            return _CT_NONE

        if self._search_pos < len(self._search_order):
            self._maybe_switch_to_next_search_region()
            return _CT_NONE

        self._search_active = False
        self._next_probe_time = elapsed + self._probe_interval
        best_r = self._best_region_by_history()
        if best_r != cur_region:
            self.env.switch_region(best_r)
        return _CT_NONE
