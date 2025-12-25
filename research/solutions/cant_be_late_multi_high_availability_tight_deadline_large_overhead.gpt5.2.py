import json
import math
from argparse import Namespace

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

        self._inited = False
        self._num_regions = 1

        self._work_done = 0.0
        self._task_done_len = 0

        self._alpha = None
        self._beta = None
        self._total_obs = 0

        self._last_region = None
        self._consec_no_spot = 0
        self._od_mode = False

        self._task_duration_total = None
        self._deadline_total = None
        self._restart_overhead_total = None

        self._CT_SPOT = ClusterType.SPOT
        self._CT_OD = ClusterType.ON_DEMAND
        self._CT_NONE = getattr(ClusterType, "NONE", getattr(ClusterType, "None", None))
        if self._CT_NONE is None:
            self._CT_NONE = ClusterType(0)  # best-effort fallback

        return self

    def _ensure_init(self):
        if self._inited:
            return
        self._inited = True

        try:
            self._num_regions = int(self.env.get_num_regions())
        except Exception:
            self._num_regions = 1

        # High-availability prior: mean ~ 0.9
        a0, b0 = 9.0, 1.0
        self._alpha = [a0 for _ in range(self._num_regions)]
        self._beta = [b0 for _ in range(self._num_regions)]
        self._total_obs = int((a0 + b0) * self._num_regions)

        self._last_region = None
        self._consec_no_spot = 0
        self._od_mode = False

        td = getattr(self, "task_duration", 0.0)
        dl = getattr(self, "deadline", 0.0)
        ro = getattr(self, "restart_overhead", 0.0)

        if isinstance(td, (list, tuple)):
            td = float(sum(td))
        else:
            td = float(td)

        if isinstance(dl, (list, tuple)):
            dl = float(dl[0]) if dl else 0.0
        else:
            dl = float(dl)

        if isinstance(ro, (list, tuple)):
            ro = float(ro[0]) if ro else 0.0
        else:
            ro = float(ro)

        self._task_duration_total = td
        self._deadline_total = dl
        self._restart_overhead_total = ro

    def _update_work_done(self):
        tdt = getattr(self, "task_done_time", None)
        if not tdt:
            return
        n = len(tdt)
        if n <= self._task_done_len:
            return
        # Usually only one new entry per step; summing a short slice is fine.
        self._work_done += float(sum(tdt[self._task_done_len : n]))
        self._task_done_len = n

    def _observe_spot(self, region: int, has_spot: bool):
        if region is None:
            return
        if region < 0 or region >= self._num_regions:
            return
        if has_spot:
            self._alpha[region] += 1.0
        else:
            self._beta[region] += 1.0
        self._total_obs += 1

    def _select_region_ucb(self, exclude_region: int):
        if self._num_regions <= 1:
            return exclude_region if exclude_region is not None else 0

        total = max(1.0, float(self._total_obs))
        logt = math.log(total + 1.0)
        c = 0.6

        best_r = None
        best_score = -1e18

        for r in range(self._num_regions):
            if exclude_region is not None and r == exclude_region:
                continue
            a = self._alpha[r]
            b = self._beta[r]
            n = a + b
            mean = a / n
            bonus = c * math.sqrt(logt / n)
            score = mean + bonus
            if score > best_score:
                best_score = score
                best_r = r

        if best_r is None:
            best_r = (exclude_region + 1) % self._num_regions if exclude_region is not None else 0
        return best_r

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_init()
        self._update_work_done()

        try:
            region = int(self.env.get_current_region())
        except Exception:
            region = 0

        if self._last_region is None:
            self._last_region = region
            self._consec_no_spot = 0
        elif region != self._last_region:
            self._last_region = region
            self._consec_no_spot = 0

        # Observe availability for the current region
        self._observe_spot(region, bool(has_spot))

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0))
        gap = float(getattr(self.env, "gap_seconds", 0.0))

        work_left = self._task_duration_total - self._work_done
        if work_left <= 1e-9:
            return self._CT_NONE

        remaining_time = self._deadline_total - elapsed
        if remaining_time <= 0.0:
            self._od_mode = True
            return self._CT_OD

        ro = self._restart_overhead_total
        guard = max(2.0 * gap, ro, 0.0)

        critical = remaining_time <= (work_left + ro + guard)

        # Once we enter on-demand mode, stick with it to ensure deadline.
        if self._od_mode or critical:
            self._od_mode = True
            return self._CT_OD

        if has_spot:
            self._consec_no_spot = 0
            return self._CT_SPOT

        self._consec_no_spot += 1

        # If spot is unavailable, pause to save cost, but switch regions to
        # increase chance of finding spot next step (without committing to extra cost).
        # Avoid switching if it could materially increase pending overhead time.
        try:
            pending = float(getattr(self, "remaining_restart_overhead", 0.0))
        except Exception:
            pending = 0.0

        should_switch = self._num_regions > 1 and (pending <= 1e-6 or pending >= 0.75 * ro)
        if should_switch:
            target = self._select_region_ucb(exclude_region=region)
            if target != region:
                try:
                    self.env.switch_region(target)
                except Exception:
                    pass

        return self._CT_NONE
