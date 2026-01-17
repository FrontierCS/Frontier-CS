import json
import math
from argparse import Namespace
from typing import Any, List, Optional

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

        self._mr_inited = False
        self._on_demand_committed = False

        return self

    def _get_scalar(self, x: Any) -> float:
        if isinstance(x, (list, tuple)):
            if not x:
                return 0.0
            return float(x[0])
        return float(x)

    def _get_task_done_list(self) -> List[float]:
        t = getattr(self, "task_done_time", None)
        if t is None:
            return []
        if isinstance(t, (list, tuple)) and t and isinstance(t[0], (list, tuple)):
            return list(t[0])
        if isinstance(t, (list, tuple)):
            return list(t)
        return []

    def _lazy_init(self) -> None:
        if self._mr_inited:
            return
        self._mr_inited = True

        self._gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        if self._gap <= 0:
            self._gap = 1.0

        self._deadline = self._get_scalar(getattr(self, "deadline", 0.0))
        self._task_duration = self._get_scalar(getattr(self, "task_duration", 0.0))
        self._restart_overhead = self._get_scalar(getattr(self, "restart_overhead", 0.0))

        self._n_regions = int(self.env.get_num_regions()) if hasattr(self.env, "get_num_regions") else 1
        if self._n_regions <= 0:
            self._n_regions = 1

        self._p_spot = [0.5] * self._n_regions
        self._seen = [0] * self._n_regions
        self._gamma = 0.05
        self._explore_c = 0.12

        self._consecutive_no_spot = 0
        self._last_region = int(self.env.get_current_region()) if hasattr(self.env, "get_current_region") else 0

        tdt = self._get_task_done_list()
        self._tdt_len = len(tdt)
        self._done_total = float(sum(tdt))
        self._prev_done_total = self._done_total
        self._prev_elapsed = float(getattr(self.env, "elapsed_seconds", 0.0))
        self._prev_action = ClusterType.NONE

        self._spot_eff_ewma = 1.0
        self._spot_eff_gamma = 0.05

    def _update_done_total(self) -> None:
        tdt = self._get_task_done_list()
        L = len(tdt)
        if L < self._tdt_len:
            self._tdt_len = L
            self._done_total = float(sum(tdt))
            return
        if L > self._tdt_len:
            s = 0.0
            for v in tdt[self._tdt_len :]:
                s += float(v)
            self._done_total += s
            self._tdt_len = L

    def _remaining_restart(self) -> float:
        r = getattr(self, "remaining_restart_overhead", 0.0)
        if isinstance(r, (list, tuple)):
            return float(r[0]) if r else 0.0
        try:
            return float(r)
        except Exception:
            return 0.0

    def _steps_needed(self, work_seconds: float, pending_overhead_seconds: float) -> int:
        w = float(work_seconds)
        if w <= 1e-9:
            return 0
        p = float(pending_overhead_seconds)
        if p < 0.0:
            p = 0.0
        x = (w + p) / self._gap
        return int(math.ceil(x - 1e-12))

    def _time_needed_on_demand_if_start_now(self, remaining_work: float, last_cluster_type: ClusterType) -> float:
        if last_cluster_type == ClusterType.ON_DEMAND:
            pending = self._remaining_restart()
        else:
            pending = self._restart_overhead
        steps = self._steps_needed(remaining_work, pending)
        return steps * self._gap

    def _choose_next_region_to_probe(self, current_region: int) -> int:
        best_r = current_region
        best_score = -1e18

        total_seen = 0
        for s in self._seen:
            total_seen += s
        total_seen = max(total_seen, 1)

        for r in range(self._n_regions):
            base = self._p_spot[r]
            bonus = self._explore_c / math.sqrt(self._seen[r] + 1.0)
            score = base + bonus
            if r == current_region:
                score += 0.01
            if score > best_score:
                best_score = score
                best_r = r

        if best_r == current_region and self._consecutive_no_spot >= 2:
            second_r = current_region
            second_score = -1e18
            for r in range(self._n_regions):
                if r == current_region:
                    continue
                base = self._p_spot[r]
                bonus = self._explore_c / math.sqrt(self._seen[r] + 1.0)
                score = base + bonus
                if score > second_score:
                    second_score = score
                    second_r = r
            if second_r != current_region and second_score > best_score - 0.02:
                best_r = second_r

        return best_r

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._lazy_init()

        now_elapsed = float(getattr(self.env, "elapsed_seconds", 0.0))
        self._update_done_total()
        done_total = self._done_total

        if now_elapsed > self._prev_elapsed + 1e-12:
            delta_work = done_total - self._prev_done_total
            if self._prev_action == ClusterType.SPOT:
                eff = 0.0
                if self._gap > 1e-9:
                    eff = max(0.0, min(1.0, float(delta_work) / self._gap))
                self._spot_eff_ewma = (1.0 - self._spot_eff_gamma) * self._spot_eff_ewma + self._spot_eff_gamma * eff

        self._prev_elapsed = now_elapsed
        self._prev_done_total = done_total

        current_region = int(self.env.get_current_region()) if hasattr(self.env, "get_current_region") else 0
        if current_region < 0:
            current_region = 0
        if current_region >= self._n_regions:
            current_region = self._n_regions - 1

        obs = 1.0 if has_spot else 0.0
        self._seen[current_region] += 1
        self._p_spot[current_region] = (1.0 - self._gamma) * self._p_spot[current_region] + self._gamma * obs

        remaining_work = self._task_duration - done_total
        if remaining_work <= 1e-6:
            self._prev_action = ClusterType.NONE
            self._last_region = current_region
            return ClusterType.NONE

        time_left = self._deadline - now_elapsed
        if time_left <= 0.0:
            self._on_demand_committed = True
            self._prev_action = ClusterType.ON_DEMAND
            self._last_region = current_region
            return ClusterType.ON_DEMAND

        if self._on_demand_committed:
            self._prev_action = ClusterType.ON_DEMAND
            self._last_region = current_region
            return ClusterType.ON_DEMAND

        t_need_now = self._time_needed_on_demand_if_start_now(remaining_work, last_cluster_type)
        safety_slack = self._gap

        if time_left <= t_need_now + safety_slack + 1e-9:
            self._on_demand_committed = True
            self._prev_action = ClusterType.ON_DEMAND
            self._last_region = current_region
            return ClusterType.ON_DEMAND

        time_left_next = time_left - self._gap
        t_need_next = self._steps_needed(remaining_work, self._restart_overhead) * self._gap

        if time_left_next <= t_need_next + 1e-9:
            self._on_demand_committed = True
            self._prev_action = ClusterType.ON_DEMAND
            self._last_region = current_region
            return ClusterType.ON_DEMAND

        if has_spot:
            self._consecutive_no_spot = 0
            self._prev_action = ClusterType.SPOT
            self._last_region = current_region
            return ClusterType.SPOT

        self._consecutive_no_spot += 1

        target = self._choose_next_region_to_probe(current_region)
        if target != current_region and hasattr(self.env, "switch_region"):
            try:
                self.env.switch_region(int(target))
                current_region = target
            except Exception:
                pass

        self._prev_action = ClusterType.NONE
        self._last_region = current_region
        return ClusterType.NONE