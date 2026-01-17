import json
from argparse import Namespace
from typing import List, Optional

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_multi_region_v1"

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
        self._panic = False

        self._num_regions = 0
        self._region_total: List[int] = []
        self._region_spot: List[int] = []
        self._region_no_spot_streak: List[int] = []

        self._step_idx = 0
        self._last_switch_step = -10**18
        self._rr_ptr = 0

        self._done_sum = 0.0
        self._done_len = 0

        self._gap = None
        self._task_duration_sec = None
        self._deadline_sec = None
        self._restart_overhead_sec = None

        self._risk_slack_sec = None
        self._patience_steps = None
        self._min_between_switch_steps = None
        self._switch_slack_min_sec = None

        return self

    def _init_if_needed(self) -> None:
        if self._inited:
            return
        self._inited = True

        self._gap = float(self.env.gap_seconds)

        td = getattr(self, "task_duration", None)
        if isinstance(td, list):
            td = td[0] if td else 0.0
        self._task_duration_sec = float(td)

        dl = getattr(self, "deadline", None)
        if isinstance(dl, list):
            dl = dl[0] if dl else 0.0
        self._deadline_sec = float(dl)

        oh = getattr(self, "restart_overhead", None)
        if isinstance(oh, list):
            oh = oh[0] if oh else 0.0
        self._restart_overhead_sec = float(oh)

        self._num_regions = int(self.env.get_num_regions())
        if self._num_regions < 1:
            self._num_regions = 1

        self._region_total = [0] * self._num_regions
        self._region_spot = [0] * self._num_regions
        self._region_no_spot_streak = [0] * self._num_regions

        # Keep on-demand in the last window to reduce risk; avoid scaling too much with gap.
        self._risk_slack_sec = max(3600.0, 2.0 * self._gap + 2.0 * self._restart_overhead_sec)

        patience_sec = 1800.0
        self._patience_steps = max(1, int((patience_sec + self._gap - 1e-9) // self._gap))
        self._min_between_switch_steps = self._patience_steps

        self._switch_slack_min_sec = self._risk_slack_sec + 2.0 * self._restart_overhead_sec + 900.0

    def _update_done_sum(self) -> None:
        td = self.task_done_time
        n = len(td)
        if n == self._done_len:
            return
        s = self._done_sum
        for i in range(self._done_len, n):
            s += float(td[i])
        self._done_sum = s
        self._done_len = n

    def _best_region_to_try(self, cur: int) -> Optional[int]:
        if self._num_regions <= 1:
            return None

        best_idx = None
        best_score = -1.0

        # Bayesian mean with Beta(1,1) prior:
        # score = (spot + 1) / (total + 2)
        for i in range(self._num_regions):
            if i == cur:
                continue
            tot = self._region_total[i]
            sp = self._region_spot[i]
            score = (sp + 1.0) / (tot + 2.0)
            if score > best_score + 1e-12:
                best_score = score
                best_idx = i
            elif abs(score - best_score) <= 1e-12 and best_idx is not None:
                # Tie-breaker: round-robin preference
                if ((i - self._rr_ptr) % self._num_regions) < ((best_idx - self._rr_ptr) % self._num_regions):
                    best_idx = i

        if best_idx is None:
            best_idx = (cur + 1) % self._num_regions
        return best_idx

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._init_if_needed()
        self._update_done_sum()
        self._step_idx += 1

        elapsed = float(self.env.elapsed_seconds)
        remaining_time = self._deadline_sec - elapsed
        remaining_work = self._task_duration_sec - self._done_sum

        if remaining_work <= 1e-9:
            return ClusterType.NONE

        if remaining_time <= 0.0:
            return ClusterType.ON_DEMAND

        slack = remaining_time - remaining_work

        # Panic: must ensure completion even if spot disappears from now on.
        # Use a conservative buffer for one last restart + step discretization.
        if (not self._panic) and (remaining_time <= remaining_work + self._restart_overhead_sec + 2.0 * self._gap):
            self._panic = True

        if self._panic:
            return ClusterType.ON_DEMAND

        cur = int(self.env.get_current_region())
        if cur < 0 or cur >= self._num_regions:
            cur = 0

        self._region_total[cur] += 1
        if has_spot:
            self._region_spot[cur] += 1
            self._region_no_spot_streak[cur] = 0
        else:
            self._region_no_spot_streak[cur] += 1

        # Risk window near deadline: stick to on-demand to avoid restart surprises.
        if slack <= self._risk_slack_sec:
            return ClusterType.ON_DEMAND

        if has_spot:
            # If we're already on-demand, only switch to spot if we have enough slack to afford restart overhead.
            if last_cluster_type == ClusterType.ON_DEMAND and slack <= (self._risk_slack_sec + self._restart_overhead_sec):
                return ClusterType.ON_DEMAND
            return ClusterType.SPOT

        # No spot: run on-demand, but consider switching regions to increase chance of returning to spot sooner.
        if self._num_regions > 1 and slack >= self._switch_slack_min_sec:
            streak = self._region_no_spot_streak[cur]
            should_switch = False

            if last_cluster_type == ClusterType.SPOT:
                should_switch = True
            elif streak >= self._patience_steps:
                should_switch = True

            if should_switch and (self._step_idx - self._last_switch_step) >= self._min_between_switch_steps:
                target = self._best_region_to_try(cur)
                if target is not None and target != cur:
                    self.env.switch_region(int(target))
                    self._last_switch_step = self._step_idx
                    self._rr_ptr = (int(target) + 1) % self._num_regions

        return ClusterType.ON_DEMAND