import json
import math
from argparse import Namespace
from typing import List, Optional

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_v1"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._committed_od: bool = False
        self._work_done: float = 0.0
        self._td_len: int = 0
        self._region_visits: Optional[List[int]] = None
        self._region_avail: Optional[List[int]] = None
        self._last_switch_elapsed: float = -1.0

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

        self._committed_od = False
        self._work_done = 0.0
        self._td_len = 0
        self._region_visits = None
        self._region_avail = None
        self._last_switch_elapsed = -1.0
        return self

    @staticmethod
    def _ceil_steps(work: float, overhead: float, gap: float) -> int:
        if work <= 1e-9:
            return 0
        x = (work + max(0.0, overhead)) / gap
        return int(math.ceil(x - 1e-12))

    def _time_needed(self, work: float, overhead: float, gap: float) -> float:
        steps = self._ceil_steps(work, overhead, gap)
        return steps * gap

    def _init_region_stats_if_needed(self) -> None:
        if self._region_visits is not None:
            return
        try:
            n = int(self.env.get_num_regions())
        except Exception:
            n = 1
        if n <= 0:
            n = 1
        self._region_visits = [0] * n
        self._region_avail = [0] * n

    def _update_work_done(self) -> None:
        td = self.task_done_time
        if td is None:
            return
        n = len(td)
        if n <= self._td_len:
            return
        self._work_done += sum(td[self._td_len : n])
        self._td_len = n

    def _best_region_idx(self, current_idx: int) -> int:
        self._init_region_stats_if_needed()
        assert self._region_visits is not None and self._region_avail is not None
        n = len(self._region_visits)
        if n <= 1:
            return current_idx

        best_idx = current_idx
        best_score = -1.0
        for i in range(n):
            v = self._region_visits[i]
            a = self._region_avail[i]
            score = (a + 1.0) / (v + 2.0)  # Beta(1,1) posterior mean
            if score > best_score + 1e-15 and i != current_idx:
                best_score = score
                best_idx = i

        if best_idx == current_idx:
            best_idx = (current_idx + 1) % n
        return best_idx

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._init_region_stats_if_needed()
        self._update_work_done()

        g = float(self.env.gap_seconds)
        if g <= 0.0:
            g = 1.0

        t = float(self.env.elapsed_seconds)
        remaining_time = float(self.deadline) - t
        if remaining_time <= 1e-9:
            return ClusterType.NONE

        remaining_work = float(self.task_duration) - float(self._work_done)
        if remaining_work <= 1e-6:
            return ClusterType.NONE

        # Update per-region availability stats for the current region.
        try:
            cur_region = int(self.env.get_current_region())
        except Exception:
            cur_region = 0
        if self._region_visits is not None and 0 <= cur_region < len(self._region_visits):
            self._region_visits[cur_region] += 1
            if has_spot:
                self._region_avail[cur_region] += 1

        if self._committed_od:
            return ClusterType.ON_DEMAND

        # Helper: predict work gained in the next step if we choose `choice`.
        def predict_step(choice: ClusterType) -> tuple[float, float]:
            if choice == ClusterType.NONE:
                return 0.0, 0.0
            if choice == last_cluster_type:
                overhead_to_pay = float(self.remaining_restart_overhead)
            else:
                overhead_to_pay = float(self.restart_overhead)
            if overhead_to_pay < 0.0:
                overhead_to_pay = 0.0
            work_gain = g - overhead_to_pay
            if work_gain < 0.0:
                work_gain = 0.0
            overhead_rem = overhead_to_pay - g
            if overhead_rem < 0.0:
                overhead_rem = 0.0
            return work_gain, overhead_rem

        # Feasibility if we take one step with `choice`, then finish with on-demand afterwards.
        def feasible_with_fallback(choice: ClusterType) -> bool:
            work_gain, overhead_rem = predict_step(choice)
            rw2 = remaining_work - work_gain
            if rw2 < 0.0:
                rw2 = 0.0
            rt2 = remaining_time - g
            if rt2 < -1e-9:
                return False
            if rw2 <= 1e-9:
                return True

            if choice == ClusterType.ON_DEMAND:
                overhead_next = overhead_rem
            else:
                overhead_next = float(self.restart_overhead)
                if overhead_next < 0.0:
                    overhead_next = 0.0

            need = self._time_needed(rw2, overhead_next, g)
            return need <= rt2 + 1e-6

        # If spot is available, prefer spot if it keeps a safe on-demand fallback.
        if has_spot:
            if feasible_with_fallback(ClusterType.SPOT):
                return ClusterType.SPOT
            self._committed_od = True
            return ClusterType.ON_DEMAND

        # No spot: prefer pausing if safe, potentially switching region to find spot sooner.
        if feasible_with_fallback(ClusterType.NONE):
            if self._region_visits is not None and len(self._region_visits) > 1:
                # Switch while idle; overhead does not stack and we aren't risking SPOT errors.
                if self._last_switch_elapsed < 0.0 or (t - self._last_switch_elapsed) >= g - 1e-9:
                    best = self._best_region_idx(cur_region)
                    if best != cur_region:
                        try:
                            self.env.switch_region(best)
                            self._last_switch_elapsed = t
                        except Exception:
                            pass
            return ClusterType.NONE

        # Must use on-demand to meet the deadline.
        self._committed_od = True
        return ClusterType.ON_DEMAND