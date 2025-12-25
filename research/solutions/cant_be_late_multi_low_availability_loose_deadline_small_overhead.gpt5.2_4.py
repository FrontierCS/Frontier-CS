import json
import math
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_v3"

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
        self._committed_on_demand = False

        self._done_sum = 0.0
        self._last_done_len = 0

        self._num_regions = None
        self._spot_ema = None
        self._spot_counts = None
        self._idle_streak = 0

        self._ema_gamma = 0.06
        self._explore_c = 0.25
        self._idle_switch_interval = 6

        return self

    def _lazy_init(self) -> None:
        if self._inited:
            return
        try:
            self._num_regions = int(self.env.get_num_regions())
        except Exception:
            self._num_regions = 1
        self._spot_ema = [0.5] * self._num_regions
        self._spot_counts = [0] * self._num_regions
        self._inited = True

    @staticmethod
    def _as_scalar(x):
        if isinstance(x, (list, tuple)):
            return float(x[0]) if x else 0.0
        return float(x)

    def _update_done_sum(self) -> None:
        tdt = self.task_done_time
        if tdt is None:
            return
        n = len(tdt)
        if n == self._last_done_len:
            return
        if n < self._last_done_len:
            self._done_sum = float(sum(tdt))
            self._last_done_len = n
            return
        inc = 0.0
        for v in tdt[self._last_done_len : n]:
            inc += float(v)
        self._done_sum += inc
        self._last_done_len = n

    @staticmethod
    def _wall_time_needed_seconds(remaining_work: float, overhead0: float, gap: float) -> float:
        if remaining_work <= 0.0:
            return 0.0
        if gap <= 0.0:
            return float("inf")
        work_first = gap - overhead0
        if work_first < 0.0:
            work_first = 0.0
        if remaining_work <= work_first + 1e-9:
            return gap
        rem = remaining_work - work_first
        steps_more = int(math.ceil(rem / gap - 1e-12))
        if steps_more < 0:
            steps_more = 0
        return (1 + steps_more) * gap

    def _choose_region_to_probe(self) -> int:
        n = self._num_regions
        if n <= 1:
            return 0
        best = 0
        best_score = -1e18
        for i in range(n):
            ema = self._spot_ema[i]
            c = self._spot_counts[i]
            score = ema + self._explore_c / math.sqrt(1.0 + c)
            if score > best_score:
                best_score = score
                best = i
        return best

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._lazy_init()
        self._update_done_sum()

        task_duration = self._as_scalar(self.task_duration)
        deadline = self._as_scalar(self.deadline)
        restart_overhead = self._as_scalar(self.restart_overhead)
        gap = float(self.env.gap_seconds)

        remaining_work = task_duration - self._done_sum
        if remaining_work <= 1e-9:
            self._committed_on_demand = True
            self._idle_streak = 0
            return ClusterType.NONE

        now = float(self.env.elapsed_seconds)
        time_left = deadline - now
        if time_left <= 0.0:
            self._committed_on_demand = True
            self._idle_streak = 0
            return ClusterType.ON_DEMAND

        try:
            region = int(self.env.get_current_region())
        except Exception:
            region = 0
        if 0 <= region < self._num_regions:
            self._spot_counts[region] += 1
            g = self._ema_gamma
            self._spot_ema[region] = (1.0 - g) * self._spot_ema[region] + g * (1.0 if has_spot else 0.0)

        commit_extra = max(3.0 * restart_overhead, 0.05 * gap)
        safety_time = min(gap, 6.0 * restart_overhead)

        if self._committed_on_demand:
            self._idle_streak = 0
            return ClusterType.ON_DEMAND

        if last_cluster_type == ClusterType.ON_DEMAND:
            overhead0 = float(self.remaining_restart_overhead) if self.remaining_restart_overhead is not None else 0.0
            if overhead0 < 0.0:
                overhead0 = 0.0
        else:
            overhead0 = restart_overhead

        wall_needed_now = self._wall_time_needed_seconds(remaining_work, overhead0, gap) + safety_time
        if time_left <= wall_needed_now + commit_extra:
            self._committed_on_demand = True
            self._idle_streak = 0
            return ClusterType.ON_DEMAND

        if has_spot:
            self._idle_streak = 0
            return ClusterType.SPOT

        time_left_after_idle = time_left - gap
        wall_needed_after_idle = self._wall_time_needed_seconds(remaining_work, restart_overhead, gap) + safety_time
        if time_left_after_idle >= wall_needed_after_idle + commit_extra:
            self._idle_streak += 1
            if self._num_regions > 1 and (self._idle_streak == 1 or (self._idle_streak % self._idle_switch_interval) == 0):
                target = self._choose_region_to_probe()
                if target != region:
                    try:
                        self.env.switch_region(int(target))
                    except Exception:
                        pass
            return ClusterType.NONE

        self._committed_on_demand = True
        self._idle_streak = 0
        return ClusterType.ON_DEMAND
