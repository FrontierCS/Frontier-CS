import json
import math
from argparse import Namespace
from typing import Optional

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


_CT_SPOT = getattr(ClusterType, "SPOT")
_CT_ON_DEMAND = getattr(ClusterType, "ON_DEMAND")
_CT_NONE = getattr(ClusterType, "NONE", getattr(ClusterType, "None"))


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_multi_region_v1"

    def solve(self, spec_path: str) -> "Solution":
        with open(spec_path, "r") as f:
            config = json.load(f)

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)

        self._initialized = False
        self._done_work = 0.0
        self._done_len = 0

        self._alpha = None
        self._beta = None
        self._total_obs = 0

        self._region_enter_elapsed = 0.0
        self._consec_no_spot = 0
        self._last_switch_elapsed = -1e18

        return self

    def _init_if_needed(self) -> None:
        if self._initialized:
            return
        n = int(self.env.get_num_regions())
        self._alpha = [1.0] * n
        self._beta = [1.0] * n
        self._total_obs = 0

        self._done_work = 0.0
        self._done_len = 0

        self._region_enter_elapsed = float(getattr(self.env, "elapsed_seconds", 0.0))
        self._consec_no_spot = 0
        self._last_switch_elapsed = -1e18

        self._initialized = True

    def _update_done_work(self) -> None:
        td = self.task_done_time
        ln = len(td)
        if ln <= self._done_len:
            return
        new_sum = 0.0
        for i in range(self._done_len, ln):
            new_sum += float(td[i])
        self._done_work += new_sum
        self._done_len = ln

    def _seconds(self, x) -> float:
        if isinstance(x, (list, tuple)):
            return float(x[0])
        return float(x)

    def _choose_best_region_ucb(self, current: int) -> Optional[int]:
        n = len(self._alpha)
        if n <= 1:
            return None
        total = max(1, self._total_obs)
        best_idx = None
        best_score = -1e18
        logt = math.log(total + 1.0)
        for i in range(n):
            if i == current:
                continue
            a = self._alpha[i]
            b = self._beta[i]
            obs_i = max(0.0, a + b - 2.0)
            mean = a / (a + b)
            bonus = math.sqrt(2.0 * logt / (obs_i + 1.0))
            score = mean + bonus
            if score > best_score:
                best_score = score
                best_idx = i
        return best_idx

    def _panic_mode(self, last_cluster_type: ClusterType, time_left: float, work_left: float) -> bool:
        gap = float(self.env.gap_seconds)
        restart_overhead = self._seconds(self.restart_overhead)
        remaining_restart = float(getattr(self, "remaining_restart_overhead", 0.0))

        if last_cluster_type == _CT_ON_DEMAND:
            start_overhead = max(0.0, remaining_restart)
        else:
            start_overhead = restart_overhead

        # Add conservative buffer for at least one more disruption and step discretization.
        margin = max(gap, 2.0 * restart_overhead) + 0.25 * restart_overhead
        need = work_left + start_overhead + margin
        return time_left <= need

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._init_if_needed()
        self._update_done_work()

        task_duration = self._seconds(self.task_duration)
        deadline = self._seconds(self.deadline)
        elapsed = float(self.env.elapsed_seconds)

        if self._done_work >= task_duration - 1e-6:
            return _CT_NONE

        current_region = int(self.env.get_current_region())
        self._total_obs += 1
        if has_spot:
            self._alpha[current_region] += 1.0
            self._consec_no_spot = 0
        else:
            self._beta[current_region] += 1.0
            self._consec_no_spot += 1

        work_left = max(0.0, task_duration - self._done_work)
        time_left = max(0.0, deadline - elapsed)

        # Panic mode: guarantee completion via on-demand and avoid region switches.
        if self._panic_mode(last_cluster_type, time_left, work_left):
            return _CT_ON_DEMAND

        # Not in panic: exploit spot whenever available.
        if has_spot:
            if last_cluster_type == _CT_ON_DEMAND:
                # Switching from on-demand to spot costs a restart; only do it with ample slack.
                gap = float(self.env.gap_seconds)
                restart_overhead = self._seconds(self.restart_overhead)
                remaining_restart = float(getattr(self, "remaining_restart_overhead", 0.0))
                on_demand_need = work_left + max(0.0, remaining_restart) + max(gap, restart_overhead)
                spot_switch_need = work_left + restart_overhead + 2.0 * max(gap, restart_overhead)
                if time_left > max(on_demand_need, spot_switch_need):
                    return _CT_SPOT
                return _CT_ON_DEMAND
            return _CT_SPOT

        # Spot unavailable and not in panic: pause (free) and optionally search regions.
        if self.env.get_num_regions() > 1 and last_cluster_type != _CT_ON_DEMAND:
            gap = float(self.env.gap_seconds)
            restart_overhead = self._seconds(self.restart_overhead)

            # Switch regions only after we've observed an outage for a while and have dwelled enough.
            in_region_for = elapsed - self._region_enter_elapsed
            outage_for = self._consec_no_spot * gap

            min_dwell = max(5.0 * gap, 2.0 * restart_overhead)
            min_outage = max(2.0 * gap, restart_overhead)

            can_switch = (in_region_for >= min_dwell) and (outage_for >= min_outage) and (elapsed - self._last_switch_elapsed >= gap)
            if can_switch:
                target = self._choose_best_region_ucb(current_region)
                if target is not None and target != current_region:
                    self.env.switch_region(int(target))
                    self._region_enter_elapsed = elapsed
                    self._consec_no_spot = 0
                    self._last_switch_elapsed = elapsed

        return _CT_NONE