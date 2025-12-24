import json
from argparse import Namespace
from typing import List, Optional

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


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

        self._done_cached: float = 0.0
        self._done_len: int = 0

        self._num_regions: Optional[int] = None
        self._spot_obs: Optional[List[int]] = None
        self._spot_hits: Optional[List[int]] = None

        self._region_switch_cooldown: int = 0
        self._spot_up_streak: int = 0
        self._spot_down_streak: int = 0

        self._commit_on_demand: bool = False

        self._prior_weight: float = 40.0
        self._prior_p: float = 0.20

        return self

    def _get_done_work_seconds(self) -> float:
        td = self.task_done_time
        l = len(td)
        if l != self._done_len:
            self._done_cached += sum(td[self._done_len : l])
            self._done_len = l
        return self._done_cached

    def _ensure_region_stats(self) -> None:
        if self._num_regions is not None:
            return
        n = int(self.env.get_num_regions())
        self._num_regions = n
        self._spot_obs = [0] * n
        self._spot_hits = [0] * n

    def _estimate_region_p(self, idx: int) -> float:
        obs = self._spot_obs[idx]
        hits = self._spot_hits[idx]
        pw = self._prior_weight
        pp = self._prior_p
        return (hits + pp * pw) / (obs + pw)

    def _maybe_switch_region_during_idle(self, has_spot: bool) -> None:
        if self._num_regions is None or self._num_regions <= 1:
            return
        if self._region_switch_cooldown > 0:
            self._region_switch_cooldown -= 1
            return
        if has_spot:
            return

        cur = int(self.env.get_current_region())
        best = cur
        best_p = self._estimate_region_p(cur)

        for i in range(self._num_regions):
            if i == cur:
                continue
            p = self._estimate_region_p(i)
            if p > best_p:
                best_p = p
                best = i

        cur_p = best_p if best == cur else self._estimate_region_p(cur)
        if best != cur:
            delta = best_p - cur_p
            if delta >= 0.04 or self._spot_down_streak >= 3:
                self.env.switch_region(best)
                gap = float(self.env.gap_seconds)
                ro = float(self.restart_overhead)
                cd = int(max(1.0, ro / max(gap, 1e-9)))
                self._region_switch_cooldown = cd
                self._spot_up_streak = 0
                self._spot_down_streak = 0

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_region_stats()
        cur_region = int(self.env.get_current_region())

        self._spot_obs[cur_region] += 1
        if has_spot:
            self._spot_hits[cur_region] += 1
            self._spot_up_streak += 1
            self._spot_down_streak = 0
        else:
            self._spot_down_streak += 1
            self._spot_up_streak = 0

        done = self._get_done_work_seconds()
        remaining_work = self.task_duration - done
        if remaining_work <= 0:
            try:
                return ClusterType.NONE
            except AttributeError:
                return ClusterType.None  # type: ignore[attr-defined]

        gap = float(self.env.gap_seconds)
        elapsed = float(self.env.elapsed_seconds)
        remaining_time = self.deadline - elapsed

        ro = float(self.restart_overhead)
        slack = remaining_time - remaining_work

        commit_margin = max(1800.0, 2.0 * ro + 3.0 * gap)
        back_to_spot_slack = commit_margin + 2.0 * ro
        confirm_steps = int(max(1.0, ro / max(gap, 1e-9)))

        if (not self._commit_on_demand) and slack <= commit_margin:
            self._commit_on_demand = True

        if self._commit_on_demand:
            return ClusterType.ON_DEMAND

        if has_spot:
            if last_cluster_type == ClusterType.ON_DEMAND:
                if self._spot_up_streak >= confirm_steps and slack > back_to_spot_slack:
                    return ClusterType.SPOT
                return ClusterType.ON_DEMAND
            if last_cluster_type == ClusterType.SPOT:
                return ClusterType.SPOT
            if self._spot_up_streak >= confirm_steps and slack > back_to_spot_slack:
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND

        # No spot available in current region/time.
        # Prefer idling if we can still finish by running on-demand continuously afterward.
        if remaining_time - gap >= remaining_work + ro:
            self._maybe_switch_region_during_idle(has_spot=False)
            try:
                return ClusterType.NONE
            except AttributeError:
                return ClusterType.None  # type: ignore[attr-defined]

        return ClusterType.ON_DEMAND
