import json
import math
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


_CT_SPOT = getattr(ClusterType, "SPOT", None)
_CT_OD = getattr(ClusterType, "ON_DEMAND", None)
_CT_NONE = getattr(ClusterType, "NONE", None)
if _CT_NONE is None:
    _CT_NONE = getattr(ClusterType, "None", None)


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

        self._initialized = False
        self._committed_on_demand = False
        self._timestep = 0

        self._done_len = 0
        self._done_sum = 0.0

        self._last_switch_elapsed = -1e30
        self._unavail_streak = 0
        self._outage_switches = 0

        self._num_regions = None
        self._region_total = None
        self._region_spot_yes = None

        self._init_internal()
        return self

    def _init_internal(self) -> None:
        if self._initialized:
            return
        self._initialized = True

        try:
            n = int(self.env.get_num_regions())
        except Exception:
            n = 1
        if n <= 0:
            n = 1
        self._num_regions = n
        self._region_total = [0] * n
        self._region_spot_yes = [0] * n

    @staticmethod
    def _as_scalar(x):
        if isinstance(x, (list, tuple)):
            return float(x[0]) if x else 0.0
        return float(x)

    def _update_done_cache(self) -> float:
        tdt = self.task_done_time
        ln = len(tdt)
        if ln != self._done_len:
            s = self._done_sum
            for v in tdt[self._done_len:]:
                s += float(v)
            self._done_sum = s
            self._done_len = ln
        return self._done_sum

    @staticmethod
    def _min_steps_to_finish(remaining_work: float, pending_overhead: float, gap: float) -> int:
        if remaining_work <= 0:
            return 0
        if gap <= 0:
            return 10**18

        oh = max(0.0, pending_overhead)
        wasted_steps = int(oh // gap)
        rem = oh - wasted_steps * gap  # in [0, gap)
        first_progress = gap - rem if rem > 0.0 else gap

        if remaining_work <= first_progress + 1e-12:
            return wasted_steps + 1

        remaining_after = remaining_work - first_progress
        extra = int(math.ceil(remaining_after / gap - 1e-12))
        return wasted_steps + 1 + max(0, extra)

    def _required_time_on_demand_if_commit_now(self, last_cluster_type: ClusterType, remaining_work: float) -> float:
        gap = float(self.env.gap_seconds)
        if last_cluster_type == _CT_OD:
            pending = float(getattr(self, "remaining_restart_overhead", 0.0) or 0.0)
        else:
            pending = self._as_scalar(getattr(self, "restart_overhead", 0.0))
        steps = self._min_steps_to_finish(remaining_work, pending, gap)
        return steps * gap

    def _choose_region_to_probe(self, cur_region: int) -> int | None:
        n = self._num_regions
        if n <= 1:
            return None

        t = self._timestep + 1
        logt = math.log(t + 2.0)
        best_idx = None
        best_score = -1e30

        for i in range(n):
            if i == cur_region:
                continue
            total = self._region_total[i]
            yes = self._region_spot_yes[i]
            mean = (yes + 1.0) / (total + 2.0)
            bonus = math.sqrt(2.0 * logt / (total + 1.0))
            score = mean + 0.20 * bonus
            if score > best_score:
                best_score = score
                best_idx = i

        return best_idx

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._init_internal()
        self._timestep += 1

        gap = float(self.env.gap_seconds)
        elapsed = float(self.env.elapsed_seconds)
        deadline = self._as_scalar(getattr(self, "deadline", 0.0))
        task_duration = self._as_scalar(getattr(self, "task_duration", 0.0))
        restart_overhead = self._as_scalar(getattr(self, "restart_overhead", 0.0))

        done = self._update_done_cache()
        remaining_work = task_duration - done
        if remaining_work <= 0.0:
            return _CT_NONE

        remaining_time = deadline - elapsed
        if remaining_time <= 0.0:
            return _CT_OD

        try:
            cur_region = int(self.env.get_current_region())
        except Exception:
            cur_region = 0
        if 0 <= cur_region < self._num_regions:
            self._region_total[cur_region] += 1
            if has_spot:
                self._region_spot_yes[cur_region] += 1

        if has_spot:
            self._unavail_streak = 0
            self._outage_switches = 0
        else:
            self._unavail_streak += 1

        if self._committed_on_demand:
            return _CT_OD

        req_od_time = self._required_time_on_demand_if_commit_now(last_cluster_type, remaining_work)
        buffer = max(1800.0, gap, 3.0 * restart_overhead)
        if remaining_time <= req_od_time + buffer:
            self._committed_on_demand = True
            return _CT_OD

        if has_spot:
            return _CT_SPOT

        slack = remaining_time - req_od_time
        switch_after_steps = max(2, int(math.ceil(900.0 / gap))) if gap > 0 else 2
        cooldown = max(2.0 * gap, 1800.0)
        can_switch_time = (elapsed - self._last_switch_elapsed) >= cooldown
        can_switch_slack = slack >= max(6.0 * gap, 2.0 * restart_overhead, 3600.0)
        can_switch_outage = self._unavail_streak >= switch_after_steps
        can_switch_count = self._outage_switches < max(1, self._num_regions - 1)

        if can_switch_time and can_switch_slack and can_switch_outage and can_switch_count:
            nxt = self._choose_region_to_probe(cur_region)
            if nxt is not None and nxt != cur_region:
                try:
                    self.env.switch_region(int(nxt))
                    self._last_switch_elapsed = elapsed
                    self._outage_switches += 1
                    self._unavail_streak = 0
                except Exception:
                    pass

        return _CT_NONE