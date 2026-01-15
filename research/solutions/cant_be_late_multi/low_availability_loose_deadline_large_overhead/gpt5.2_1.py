import json
import math
from argparse import Namespace
from typing import List, Optional

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

        self._initialized: bool = False
        self._num_regions: int = 0

        self._timestep: int = 0
        self._commit_on_demand: bool = False

        self._spot_obs_total: Optional[List[int]] = None
        self._spot_obs_true: Optional[List[int]] = None
        self._last_spot_true_step: Optional[List[int]] = None

        self._cached_done: float = 0.0
        self._cached_done_len: int = 0
        self._last_elapsed_seconds: float = -1.0

        return self

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        try:
            self._num_regions = int(self.env.get_num_regions())
        except Exception:
            self._num_regions = 1
        if self._num_regions <= 0:
            self._num_regions = 1
        self._spot_obs_total = [0] * self._num_regions
        self._spot_obs_true = [0] * self._num_regions
        self._last_spot_true_step = [-10**9] * self._num_regions
        self._initialized = True

    @staticmethod
    def _as_seconds(x) -> float:
        if isinstance(x, (list, tuple)):
            if not x:
                return 0.0
            return float(x[0])
        return float(x)

    @staticmethod
    def _ceil_div(a: float, b: float) -> int:
        if b <= 0:
            return 10**18
        if a <= 0:
            return 0
        return int(math.ceil((a - 1e-12) / b))

    def _steps_left(self, time_left: float, gap: float) -> int:
        if gap <= 0:
            return 0
        if time_left <= 0:
            return 0
        return int(math.floor(time_left / gap + 1e-9))

    def _work_done_seconds(self) -> float:
        tdt = self.task_done_time
        if tdt is None:
            return 0.0
        n = len(tdt)

        if self._last_elapsed_seconds < 0 or self.env.elapsed_seconds < self._last_elapsed_seconds - 1e-9:
            self._cached_done = 0.0
            self._cached_done_len = 0

        if n < self._cached_done_len:
            self._cached_done = float(sum(tdt))
            self._cached_done_len = n
        elif n > self._cached_done_len:
            self._cached_done += float(sum(tdt[self._cached_done_len : n]))
            self._cached_done_len = n

        self._last_elapsed_seconds = float(self.env.elapsed_seconds)
        return self._cached_done

    def _choose_region_when_idle(self, current_region: int) -> int:
        if self._num_regions <= 1:
            return current_region

        t = self._timestep
        tau = 6.0

        best_idx = current_region
        best_score = -1e30

        total_obs = 1
        for i in range(self._num_regions):
            total_obs += self._spot_obs_total[i]

        log_term = math.log(total_obs + 1.0)

        for i in range(self._num_regions):
            if i == current_region:
                continue
            tot = self._spot_obs_total[i]
            tru = self._spot_obs_true[i]

            mean = (tru + 1.0) / (tot + 2.0)
            bonus = math.sqrt(2.0 * log_term / (tot + 1.0))
            ucb = mean + 0.35 * bonus

            dt = float(t - self._last_spot_true_step[i])
            recent = math.exp(-max(0.0, dt) / tau)

            score = 0.65 * recent + 0.35 * ucb
            if score > best_score:
                best_score = score
                best_idx = i

        return best_idx

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_initialized()
        self._timestep += 1

        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        if gap <= 0:
            gap = 1.0

        task_duration = self._as_seconds(getattr(self, "task_duration", 0.0))
        deadline = self._as_seconds(getattr(self, "deadline", 0.0))
        restart_overhead = self._as_seconds(getattr(self, "restart_overhead", 0.0))
        remaining_restart_overhead = self._as_seconds(getattr(self, "remaining_restart_overhead", 0.0))

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        time_left = deadline - elapsed

        current_region = 0
        try:
            current_region = int(self.env.get_current_region())
        except Exception:
            current_region = 0
        if current_region < 0:
            current_region = 0
        if current_region >= self._num_regions:
            current_region = self._num_regions - 1

        self._spot_obs_total[current_region] += 1
        if has_spot:
            self._spot_obs_true[current_region] += 1
            self._last_spot_true_step[current_region] = self._timestep

        done = self._work_done_seconds()
        work_left = task_duration - done
        if work_left <= 1e-9:
            return ClusterType.NONE

        steps_left = self._steps_left(time_left, gap)
        if steps_left <= 0:
            return ClusterType.NONE

        # Conservative: assume (re)starting on-demand requires a restart overhead.
        # Also account for any already-pending overhead in the environment.
        start_overhead = max(restart_overhead, remaining_restart_overhead)
        steps_needed_od = self._ceil_div(work_left + start_overhead, gap)

        safety_wait_steps = 1
        max_wait_steps = steps_left - steps_needed_od

        if self._commit_on_demand:
            return ClusterType.ON_DEMAND

        if max_wait_steps <= safety_wait_steps:
            self._commit_on_demand = True
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        # Idle to save cost, and reposition to a region likely to have spot next.
        if self._num_regions > 1:
            next_region = self._choose_region_when_idle(current_region)
            if next_region != current_region:
                try:
                    self.env.switch_region(next_region)
                except Exception:
                    pass

        return ClusterType.NONE