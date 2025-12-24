import json
from argparse import Namespace
from typing import Optional, Dict, List, Tuple

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_region_guard_v1"

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
        self._reset_internal()
        return self

    def _reset_internal(self) -> None:
        self._inited = False
        self._num_regions = 1
        self._done_sum = 0.0
        self._done_idx = 0
        self._can_query_has_spot = None  # type: Optional[bool]
        self._region_total = []  # type: List[int]
        self._region_avail = []  # type: List[int]
        self._preferred_region = 0
        self._commit_on_demand = False
        self._on_demand_steps = 0

    def _ensure_init(self) -> None:
        if self._inited:
            return
        try:
            self._num_regions = int(self.env.get_num_regions())
        except Exception:
            self._num_regions = 1
        if self._num_regions <= 0:
            self._num_regions = 1
        self._region_total = [0] * self._num_regions
        self._region_avail = [0] * self._num_regions

        self._can_query_has_spot = self._detect_query_has_spot_capability()
        self._inited = True

    def _detect_query_has_spot_capability(self) -> bool:
        env = self.env
        candidates = (
            "has_spot",
            "spot_available",
            "spot_availability",
            "_has_spot",
        )
        for attr in candidates:
            if hasattr(env, attr):
                v = getattr(env, attr)
                if callable(v):
                    try:
                        r = v()
                    except Exception:
                        continue
                else:
                    r = v
                if isinstance(r, bool):
                    return True

        methods = (
            "get_has_spot",
            "get_spot_available",
            "is_spot_available",
            "has_spot_in_current_region",
        )
        for meth in methods:
            if hasattr(env, meth) and callable(getattr(env, meth)):
                try:
                    r = getattr(env, meth)()
                    if isinstance(r, bool):
                        return True
                except Exception:
                    continue
        return False

    def _query_has_spot_current_region(self) -> Optional[bool]:
        env = self.env
        candidates = (
            "has_spot",
            "spot_available",
            "spot_availability",
            "_has_spot",
        )
        for attr in candidates:
            if hasattr(env, attr):
                v = getattr(env, attr)
                if callable(v):
                    try:
                        r = v()
                    except Exception:
                        continue
                else:
                    r = v
                if isinstance(r, bool):
                    return r

        methods = (
            "get_has_spot",
            "get_spot_available",
            "is_spot_available",
            "has_spot_in_current_region",
        )
        for meth in methods:
            if hasattr(env, meth) and callable(getattr(env, meth)):
                try:
                    r = getattr(env, meth)()
                    if isinstance(r, bool):
                        return r
                except Exception:
                    continue
        return None

    def _update_done_sum(self) -> None:
        td = self.task_done_time
        n = len(td)
        i = self._done_idx
        if i >= n:
            return
        s = self._done_sum
        while i < n:
            s += float(td[i])
            i += 1
        self._done_sum = s
        self._done_idx = i

    def _region_score(self, region: int) -> float:
        tot = self._region_total[region]
        av = self._region_avail[region]
        p = (av + 1.0) / (tot + 2.0)
        if region == self._preferred_region:
            p += 0.03
        return p

    def _scan_for_spot_region(self) -> Optional[int]:
        if not self._can_query_has_spot:
            return None
        if self._num_regions <= 1:
            return None
        if getattr(self, "remaining_restart_overhead", 0.0) and self.remaining_restart_overhead > 1e-9:
            return None

        try:
            start_region = int(self.env.get_current_region())
        except Exception:
            start_region = 0

        avail_now = [False] * self._num_regions
        any_known = True

        for r in range(self._num_regions):
            try:
                self.env.switch_region(r)
            except Exception:
                continue
            hs = self._query_has_spot_current_region()
            if hs is None:
                any_known = False
                break
            self._region_total[r] += 1
            if hs:
                self._region_avail[r] += 1
                avail_now[r] = True

        if not any_known:
            self._can_query_has_spot = False
            try:
                self.env.switch_region(start_region)
            except Exception:
                pass
            return None

        best = None
        best_score = -1.0
        for r in range(self._num_regions):
            if not avail_now[r]:
                continue
            sc = self._region_score(r)
            if sc > best_score:
                best_score = sc
                best = r

        if best is None:
            try:
                self.env.switch_region(start_region)
            except Exception:
                pass
            return None

        try:
            self.env.switch_region(best)
        except Exception:
            pass
        return best

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_init()
        self._update_done_sum()

        remaining_work = self.task_duration - self._done_sum
        if remaining_work <= 1e-6:
            return ClusterType.NONE

        time_remaining = self.deadline - float(self.env.elapsed_seconds)
        if time_remaining <= 1e-6:
            return ClusterType.NONE

        gap = float(getattr(self.env, "gap_seconds", 1.0))
        if gap <= 0:
            gap = 1.0

        try:
            cur_region = int(self.env.get_current_region())
        except Exception:
            cur_region = 0

        if 0 <= cur_region < self._num_regions:
            self._region_total[cur_region] += 1
            if has_spot:
                self._region_avail[cur_region] += 1

        if last_cluster_type == ClusterType.ON_DEMAND:
            self._on_demand_steps += 1
        else:
            self._on_demand_steps = 0

        rem_overhead = float(getattr(self, "remaining_restart_overhead", 0.0))
        slack = (time_remaining - rem_overhead) - remaining_work

        safety = max(2.0 * gap, 0.0)
        if not self._commit_on_demand:
            if remaining_work + float(self.restart_overhead) >= time_remaining - safety:
                self._commit_on_demand = True
            elif slack <= gap:
                self._commit_on_demand = True

        if self._commit_on_demand:
            return ClusterType.ON_DEMAND

        if rem_overhead > 1e-9:
            if last_cluster_type == ClusterType.SPOT and has_spot:
                self._preferred_region = cur_region
                return ClusterType.SPOT
            if last_cluster_type == ClusterType.ON_DEMAND:
                return ClusterType.ON_DEMAND
            if has_spot:
                self._preferred_region = cur_region
                return ClusterType.SPOT
            if slack > 4.0 * gap:
                return ClusterType.NONE
            return ClusterType.ON_DEMAND

        allow_switch_for_spot = slack > (float(self.restart_overhead) + 2.0 * gap)

        if has_spot:
            if last_cluster_type == ClusterType.ON_DEMAND:
                if slack > 6.0 * gap and self._on_demand_steps >= 2:
                    self._preferred_region = cur_region
                    return ClusterType.SPOT
                return ClusterType.ON_DEMAND
            self._preferred_region = cur_region
            return ClusterType.SPOT

        if allow_switch_for_spot:
            best = self._scan_for_spot_region()
            if best is not None:
                self._preferred_region = best
                return ClusterType.SPOT

        if slack > 6.0 * gap:
            return ClusterType.NONE

        return ClusterType.ON_DEMAND
