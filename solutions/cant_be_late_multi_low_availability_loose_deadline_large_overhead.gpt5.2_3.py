import json
import math
from argparse import Namespace
from typing import Optional

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


_SPOT = ClusterType.SPOT
_ON_DEMAND = getattr(ClusterType, "ON_DEMAND", None)
if _ON_DEMAND is None:
    _ON_DEMAND = getattr(ClusterType, "ONDEMAND", None)
_NONE = getattr(ClusterType, "NONE", None)
if _NONE is None:
    _NONE = getattr(ClusterType, "None", None)


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_ucb_safe_v1"

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
        self._gap = 0.0
        self._n_regions = 0
        self._seen = None
        self._avail = None
        self._total_seen = 0

        self._last_region: Optional[int] = None
        self._no_spot_streak = 0

        self._done_sum = 0.0
        self._done_idx = 0

        self._od_mode = False

        self._ucb_c = 0.35
        self._switch_after = 2

        return self

    def _ensure_init(self) -> None:
        if self._inited:
            return
        self._gap = float(self.env.gap_seconds)
        self._n_regions = int(self.env.get_num_regions())
        self._seen = [0] * self._n_regions
        self._avail = [0] * self._n_regions
        self._total_seen = 0
        self._last_region = int(self.env.get_current_region())
        self._no_spot_streak = 0
        self._done_sum = 0.0
        self._done_idx = 0
        self._od_mode = False
        self._inited = True

    @staticmethod
    def _as_float_seconds(x):
        if isinstance(x, (list, tuple)):
            return float(x[0])
        return float(x)

    def _steps_needed(self, work_seconds: float, start_overhead_seconds: float) -> int:
        if work_seconds <= 1e-12:
            return 0
        gap = self._gap
        overhead = max(0.0, start_overhead_seconds)

        if overhead <= 1e-12:
            return int(math.ceil(work_seconds / gap - 1e-12))

        full_overhead_steps = int(overhead // gap)
        overhead_rem = overhead - full_overhead_steps * gap

        if overhead_rem <= 1e-12:
            # After full_overhead_steps steps, next step has full work.
            return full_overhead_steps + int(math.ceil(work_seconds / gap - 1e-12))

        first_work = max(0.0, gap - overhead_rem)
        if work_seconds <= first_work + 1e-12:
            return full_overhead_steps + 1

        rem = work_seconds - first_work
        return full_overhead_steps + 1 + int(math.ceil(rem / gap - 1e-12))

    def _work_this_step(self, overhead_seconds: float) -> float:
        if overhead_seconds <= 1e-12:
            return self._gap
        if overhead_seconds >= self._gap - 1e-12:
            return 0.0
        return self._gap - overhead_seconds

    def _maybe_switch_region(self) -> None:
        n = self._n_regions
        if n <= 1:
            return

        cur = int(self.env.get_current_region())
        total = self._total_seen + 1
        log_total = math.log(total + 1.0)

        best = cur
        best_score = -1e30

        for r in range(n):
            seen = self._seen[r]
            avail = self._avail[r]
            mean = (avail + 1.0) / (seen + 2.0)
            bonus = self._ucb_c * math.sqrt(log_total / (seen + 1.0))
            score = mean + bonus
            if score > best_score:
                best_score = score
                best = r

        if best == cur:
            if self._no_spot_streak < self._switch_after:
                return
            # Pick a second-best to avoid being stuck
            second = -1
            second_score = -1e30
            for r in range(n):
                if r == cur:
                    continue
                seen = self._seen[r]
                avail = self._avail[r]
                mean = (avail + 1.0) / (seen + 2.0)
                bonus = self._ucb_c * math.sqrt(log_total / (seen + 1.0))
                score = mean + bonus
                if score > second_score:
                    second_score = score
                    second = r
            if second != -1:
                best = second
            else:
                best = (cur + 1) % n

        if best != cur:
            self.env.switch_region(best)
            self._last_region = best
            self._no_spot_streak = 0

    def _update_work_done(self) -> None:
        tdt = self.task_done_time
        ln = len(tdt)
        i = self._done_idx
        if ln > i:
            s = self._done_sum
            for j in range(i, ln):
                s += float(tdt[j])
            self._done_sum = s
            self._done_idx = ln

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_init()

        cur_region = int(self.env.get_current_region())
        if self._last_region != cur_region:
            self._last_region = cur_region
            self._no_spot_streak = 0

        self._seen[cur_region] += 1
        if has_spot:
            self._avail[cur_region] += 1
            self._no_spot_streak = 0
        else:
            self._no_spot_streak += 1
        self._total_seen += 1

        self._update_work_done()

        task_duration = self._as_float_seconds(self.task_duration)
        deadline = self._as_float_seconds(self.deadline)
        restart_overhead = self._as_float_seconds(self.restart_overhead)
        remaining_overhead = float(getattr(self, "remaining_restart_overhead", 0.0) or 0.0)

        remaining_work = task_duration - self._done_sum
        if remaining_work <= 1e-9:
            return _NONE

        remaining_time = deadline - float(self.env.elapsed_seconds)
        if remaining_time <= 1e-12:
            return _NONE

        steps_left = int(math.ceil(remaining_time / self._gap - 1e-12))
        if steps_left <= 0:
            return _NONE

        if last_cluster_type == _ON_DEMAND:
            self._od_mode = True

        if self._od_mode:
            return _ON_DEMAND

        overhead_od_now = remaining_overhead if last_cluster_type == _ON_DEMAND else restart_overhead
        overhead_spot_now = remaining_overhead if last_cluster_type == _SPOT else restart_overhead

        steps_od_now = self._steps_needed(remaining_work, overhead_od_now)
        feasible_od_now = steps_od_now <= steps_left

        feasible_none_now = (1 + self._steps_needed(remaining_work, restart_overhead)) <= steps_left

        feasible_spot_cont = False
        feasible_spot_then_od = False
        if has_spot:
            steps_spot_cont = self._steps_needed(remaining_work, overhead_spot_now)
            feasible_spot_cont = steps_spot_cont <= steps_left

            work_spot_now = self._work_this_step(overhead_spot_now)
            rem_after = remaining_work - work_spot_now
            if rem_after <= 1e-9:
                feasible_spot_then_od = True
            else:
                feasible_spot_then_od = (1 + self._steps_needed(rem_after, restart_overhead)) <= steps_left

        if has_spot:
            # Maintain "OD-safe" invariant: only keep using Spot if OD remains feasible next step,
            # unless OD is already infeasible (then Spot is the only chance).
            if feasible_spot_then_od or (not feasible_od_now and feasible_spot_cont):
                return _SPOT

        if (not has_spot) and feasible_none_now:
            self._maybe_switch_region()
            return _NONE

        if feasible_od_now:
            self._od_mode = True
            return _ON_DEMAND

        # If nothing is feasible (should be rare), try to make progress with whatever is available.
        if has_spot and feasible_spot_cont:
            return _SPOT
        self._od_mode = True
        return _ON_DEMAND
