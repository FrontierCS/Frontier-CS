import json
import math
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


_CT_NONE = getattr(ClusterType, "NONE", None)
if _CT_NONE is None:
    _CT_NONE = getattr(ClusterType, "None")


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_v1"

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

        self._initialized = False
        self._committed_on_demand = False

        self._done_sum = 0.0
        self._done_len = 0

        self._num_regions = 1
        self._region_obs = None
        self._region_avail = None
        self._region_total_obs = 0

        self._ucb_c = 0.25

        return self

    def _lazy_init(self) -> None:
        if self._initialized:
            return
        try:
            self._num_regions = int(self.env.get_num_regions())
        except Exception:
            self._num_regions = 1
        if self._num_regions <= 0:
            self._num_regions = 1
        self._region_obs = [0] * self._num_regions
        self._region_avail = [0] * self._num_regions
        self._region_total_obs = 0
        self._initialized = True

    def _update_done_sum(self) -> None:
        td = self.task_done_time
        n = len(td)
        if n <= self._done_len:
            return
        s = 0.0
        for i in range(self._done_len, n):
            s += float(td[i])
        self._done_sum += s
        self._done_len = n

    def _choose_next_region(self, cur_region: int) -> int:
        n = self._num_regions
        if n <= 1:
            return cur_region

        obs = self._region_obs
        avail = self._region_avail

        for i in range(n):
            if obs[i] == 0 and i != cur_region:
                return i

        total = self._region_total_obs + 1
        log_total = math.log(total + 1.0)

        best_region = cur_region
        best_score = -1e18
        for i in range(n):
            if i == cur_region:
                continue
            oi = obs[i]
            ai = avail[i]
            mean = (ai + 1.0) / (oi + 2.0)
            bonus = self._ucb_c * math.sqrt(log_total / (oi + 1.0))
            score = mean + bonus
            if score > best_score:
                best_score = score
                best_region = i

        return best_region

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._lazy_init()
        self._update_done_sum()

        remaining_work = float(self.task_duration) - self._done_sum
        if remaining_work <= 0.0:
            return _CT_NONE

        now = float(self.env.elapsed_seconds)
        remaining_time = float(self.deadline) - now
        if remaining_time <= 0.0:
            return _CT_NONE

        try:
            cur_region = int(self.env.get_current_region())
        except Exception:
            cur_region = 0
        if cur_region < 0 or cur_region >= self._num_regions:
            cur_region = 0

        if self._region_obs is not None:
            self._region_obs[cur_region] += 1
            self._region_total_obs += 1
            if has_spot:
                self._region_avail[cur_region] += 1

        if last_cluster_type == ClusterType.ON_DEMAND:
            self._committed_on_demand = True

        if self._committed_on_demand:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        gap = float(self.env.gap_seconds)
        overhead = float(self.restart_overhead)

        # Safe to idle this next step (do NONE) iff starting ON_DEMAND after idling
        # can still finish by deadline: remaining_work <= remaining_time - gap - overhead
        safe_to_wait = (remaining_time - gap - overhead) >= remaining_work - 1e-9

        if safe_to_wait:
            if self.remaining_restart_overhead <= 1e-9 and self._num_regions > 1:
                nxt = self._choose_next_region(cur_region)
                if nxt != cur_region:
                    try:
                        self.env.switch_region(nxt)
                    except Exception:
                        pass
            return _CT_NONE

        self._committed_on_demand = True
        return ClusterType.ON_DEMAND