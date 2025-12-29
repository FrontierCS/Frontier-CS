import json
import math
from argparse import Namespace
from typing import Optional, List

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

        self._init_done_cache()
        self._commit_on_demand = False

        self._n_regions: Optional[int] = None
        self._alpha_up: Optional[List[float]] = None
        self._alpha_total: Optional[List[float]] = None
        self._total_obs: float = 0.0

        self._down_streak = 0
        self._switches_in_streak = 0
        self._last_region: Optional[int] = None

        return self

    def _init_done_cache(self) -> None:
        self._done_len = 0
        self._done_sum = 0.0

    def _update_done_cache(self) -> float:
        td = self.task_done_time
        l = len(td)
        if l > self._done_len:
            s = self._done_sum
            for i in range(self._done_len, l):
                s += float(td[i])
            self._done_sum = s
            self._done_len = l
        return self._done_sum

    def _lazy_init_regions(self) -> None:
        if self._n_regions is not None:
            return
        try:
            n = int(self.env.get_num_regions())
        except Exception:
            n = 1
        if n <= 0:
            n = 1
        self._n_regions = n
        # Beta(1,1) prior => mean 0.5
        self._alpha_up = [1.0] * n
        self._alpha_total = [2.0] * n
        self._total_obs = 0.0

    def _update_region_stats(self, region: int, has_spot: bool) -> None:
        if self._alpha_up is None or self._alpha_total is None:
            return
        if region < 0 or region >= self._n_regions:
            return
        self._alpha_total[region] += 1.0
        if has_spot:
            self._alpha_up[region] += 1.0
        self._total_obs += 1.0

    def _pick_best_other_region(self, current: int) -> int:
        n = self._n_regions or 1
        if n <= 1:
            return current
        up = self._alpha_up
        tot = self._alpha_total
        if up is None or tot is None:
            return (current + 1) % n

        logt = math.log(self._total_obs + 2.0)
        best_idx = current
        best_score = -1e18
        for r in range(n):
            if r == current:
                continue
            tr = tot[r]
            if tr <= 0.0:
                tr = 1.0
            mean = up[r] / tr
            bonus = 0.35 * math.sqrt(logt / tr)
            score = mean + bonus
            if score > best_score:
                best_score = score
                best_idx = r
        return best_idx

    def _must_commit_on_demand(self, remaining_work: float, time_remaining: float, last_cluster_type: ClusterType, has_spot: bool) -> bool:
        if remaining_work <= 0.0:
            return False
        if time_remaining <= 0.0:
            return True

        gap = float(getattr(self.env, "gap_seconds", 1.0) or 1.0)
        overhead = float(self.restart_overhead)

        # Conservative cushion to absorb step discretization + jitter in restart modeling.
        buffer = overhead + 2.0 * gap
        if buffer > 1800.0:
            buffer = 1800.0

        # If we are not making progress (no spot), ensure we don't wait too long.
        if not has_spot:
            # If waiting one more step could jeopardize the on-demand-only completion plan, commit now.
            if time_remaining - gap <= remaining_work + overhead + buffer:
                return True

        # General "last safe point" to still finish with on-demand after paying restart overhead once.
        if time_remaining <= remaining_work + overhead + buffer:
            return True

        # If already on-demand for some reason, prefer to keep it to avoid thrash.
        if last_cluster_type == ClusterType.ON_DEMAND:
            return True

        return False

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._lazy_init_regions()

        done = self._update_done_cache()
        remaining_work = float(self.task_duration) - float(done)
        if remaining_work <= 0.0:
            return ClusterType.NONE

        elapsed = float(self.env.elapsed_seconds)
        time_remaining = float(self.deadline) - elapsed
        if time_remaining <= 0.0:
            return ClusterType.NONE

        cur_region = int(self.env.get_current_region())
        if self._last_region is None:
            self._last_region = cur_region
        self._update_region_stats(cur_region, bool(has_spot))

        if self._commit_on_demand:
            return ClusterType.ON_DEMAND

        if self._must_commit_on_demand(remaining_work, time_remaining, last_cluster_type, bool(has_spot)):
            self._commit_on_demand = True
            return ClusterType.ON_DEMAND

        # Not committed: use spot whenever possible; otherwise pause (NONE) and optionally switch regions.
        if has_spot:
            self._down_streak = 0
            self._switches_in_streak = 0
            return ClusterType.SPOT

        # Spot unavailable: consider region switch while pausing.
        self._down_streak += 1
        n = self._n_regions or 1
        if n > 1:
            gap = float(getattr(self.env, "gap_seconds", 1.0) or 1.0)
            overhead = float(self.restart_overhead)
            cooldown_steps = int(max(1.0, overhead / gap)) if gap > 0.0 else 1
            max_switches = min(3, n - 1)

            do_switch = False
            if self._switches_in_streak < max_switches:
                if self._down_streak == 1:
                    do_switch = True
                elif cooldown_steps > 0 and (self._down_streak % cooldown_steps) == 0:
                    do_switch = True

            if do_switch:
                new_region = self._pick_best_other_region(cur_region)
                if new_region != cur_region:
                    try:
                        self.env.switch_region(new_region)
                        self._switches_in_streak += 1
                        self._last_region = new_region
                    except Exception:
                        pass

        return ClusterType.NONE