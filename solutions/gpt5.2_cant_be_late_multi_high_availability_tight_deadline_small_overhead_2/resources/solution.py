import json
import math
from argparse import Namespace
from typing import Optional, List

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

        self._task_duration_s = self._as_scalar_seconds(getattr(self, "task_duration", 0.0))
        self._deadline_s = self._as_scalar_seconds(getattr(self, "deadline", 0.0))
        self._restart_overhead_s = self._as_scalar_seconds(getattr(self, "restart_overhead", 0.0))

        self._td_idx = 0
        self._work_done_s = 0.0
        self._force_od = False

        self._region_obs: Optional[List[int]] = None
        self._region_spot: Optional[List[int]] = None
        self._obs_total = 0

        return self

    @staticmethod
    def _as_scalar_seconds(x) -> float:
        if isinstance(x, (list, tuple)):
            if not x:
                return 0.0
            return float(x[0])
        return float(x)

    def _update_work_done(self) -> None:
        tdt = getattr(self, "task_done_time", None)
        if not tdt:
            return
        n = len(tdt)
        i = self._td_idx
        if i >= n:
            return
        s = self._work_done_s
        while i < n:
            s += float(tdt[i])
            i += 1
        self._td_idx = i
        self._work_done_s = s

    def _ensure_region_stats(self) -> None:
        if self._region_obs is not None:
            return
        try:
            n = int(self.env.get_num_regions())
        except Exception:
            n = 1
        if n <= 0:
            n = 1
        self._region_obs = [0] * n
        self._region_spot = [0] * n
        self._obs_total = 0

    def _record_region_obs(self, region_idx: int, has_spot: bool) -> None:
        self._ensure_region_stats()
        if self._region_obs is None or self._region_spot is None:
            return
        if 0 <= region_idx < len(self._region_obs):
            self._region_obs[region_idx] += 1
            self._region_spot[region_idx] += 1 if has_spot else 0
            self._obs_total += 1

    def _pick_region_ucb(self, current_region: int) -> int:
        self._ensure_region_stats()
        obs = self._region_obs
        spot = self._region_spot
        if obs is None or spot is None:
            return current_region
        n = len(obs)
        if n <= 1:
            return current_region

        t = max(1, self._obs_total)
        logt = math.log(t + 1.0)

        best_idx = current_region
        best_score = -1e30
        second_idx = current_region
        second_score = -1e30

        for i in range(n):
            ni = obs[i]
            if ni <= 0:
                score = 1e9
            else:
                mean = spot[i] / ni
                score = mean + math.sqrt(2.0 * logt / ni)
            if score > best_score:
                second_score, second_idx = best_score, best_idx
                best_score, best_idx = score, i
            elif score > second_score:
                second_score, second_idx = score, i

        if best_idx == current_region:
            if second_idx != current_region:
                return second_idx
            return (current_region + 1) % n
        return best_idx

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._update_work_done()

        if self._task_duration_s <= 0.0:
            self._task_duration_s = self._as_scalar_seconds(getattr(self, "task_duration", 0.0))
        if self._deadline_s <= 0.0:
            self._deadline_s = self._as_scalar_seconds(getattr(self, "deadline", 0.0))
        if self._restart_overhead_s <= 0.0:
            self._restart_overhead_s = self._as_scalar_seconds(getattr(self, "restart_overhead", 0.0))

        remaining_work = self._task_duration_s - self._work_done_s
        if remaining_work <= 1e-9:
            self._force_od = False
            return ClusterType.NONE

        try:
            elapsed = float(self.env.elapsed_seconds)
        except Exception:
            elapsed = 0.0

        remaining_time = self._deadline_s - elapsed
        if remaining_time <= 1e-9:
            self._force_od = True
            if has_spot:
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND

        try:
            gap = float(self.env.gap_seconds)
        except Exception:
            gap = 1.0
        if gap <= 0.0:
            gap = 1.0

        try:
            cur_region = int(self.env.get_current_region())
        except Exception:
            cur_region = 0

        self._record_region_obs(cur_region, has_spot)

        # Maintain feasibility to finish using on-demand if spot disappears.
        # Slack is time that can be lost to overhead/pauses.
        slack = remaining_time - remaining_work

        # If slack is already below required restart overhead, we're in a risky zone:
        # switch to on-demand whenever possible (it may still be infeasible, but is safest).
        if slack <= self._restart_overhead_s + 1e-9:
            self._force_od = True

        if self._force_od or last_cluster_type == ClusterType.ON_DEMAND:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        # No spot: either wait (NONE) or go on-demand.
        # Wait only if after waiting one full step, starting on-demand is still feasible:
        # remaining_time - gap >= remaining_work + restart_overhead
        if remaining_time - gap >= remaining_work + self._restart_overhead_s - 1e-9:
            # Explore a better region while idling to increase chance of spot next step.
            try:
                nreg = int(self.env.get_num_regions())
            except Exception:
                nreg = 1
            if nreg > 1:
                new_region = self._pick_region_ucb(cur_region)
                if new_region != cur_region:
                    try:
                        self.env.switch_region(new_region)
                    except Exception:
                        pass
            return ClusterType.NONE

        self._force_od = True
        return ClusterType.ON_DEMAND
