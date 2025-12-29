import json
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
        self._done = 0.0
        self._td_len = 0

        self._gap = None
        self._task_duration_s = None
        self._deadline_s = None
        self._restart_overhead_s = None

        self._eps = 1e-9
        self._switch_margin_s = 0.0

        self._hunt_ptr = 0
        return self

    def _init_if_needed(self) -> None:
        if self._inited:
            return

        self._gap = float(getattr(self.env, "gap_seconds", 1.0))

        td = getattr(self, "task_duration", None)
        if isinstance(td, (list, tuple)):
            td = td[0] if td else 0.0
        self._task_duration_s = float(td if td is not None else 0.0)

        dl = getattr(self, "deadline", None)
        if isinstance(dl, (list, tuple)):
            dl = dl[0] if dl else 0.0
        self._deadline_s = float(dl if dl is not None else 0.0)

        ro = getattr(self, "restart_overhead", None)
        if isinstance(ro, (list, tuple)):
            ro = ro[0] if ro else 0.0
        self._restart_overhead_s = float(ro if ro is not None else 0.0)

        # Margin to avoid flip-flopping when slack is tiny; scale with gap but keep small.
        self._switch_margin_s = max(1e-6, 0.001 * self._gap)

        self._inited = True

    def _update_done(self) -> None:
        td = self.task_done_time
        n = len(td)
        if n <= self._td_len:
            return
        if n == self._td_len + 1:
            self._done += float(td[-1])
        else:
            self._done += float(sum(td[self._td_len : n]))
        self._td_len = n

    @staticmethod
    def _ct_none():
        return getattr(ClusterType, "NONE", getattr(ClusterType, "None"))

    def _hunt_region_if_waiting(self) -> None:
        try:
            num = int(self.env.get_num_regions())
        except Exception:
            return
        if num <= 1:
            return
        try:
            cur = int(self.env.get_current_region())
        except Exception:
            cur = 0
        nxt = (cur + 1) % num
        try:
            self.env.switch_region(nxt)
        except Exception:
            pass

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._init_if_needed()
        self._update_done()

        CT_NONE = self._ct_none()
        CT_SPOT = ClusterType.SPOT
        CT_OD = ClusterType.ON_DEMAND

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0))
        time_left = self._deadline_s - elapsed
        if time_left <= 0:
            return CT_NONE

        remaining_work = self._task_duration_s - self._done
        if remaining_work <= 0:
            return CT_NONE

        slack = time_left - remaining_work

        # If already on on-demand, don't churn; it is always available.
        if last_cluster_type == CT_OD:
            return CT_OD

        if has_spot:
            # If we are NOT already on on-demand, spot is always preferred while available.
            return CT_SPOT

        # No spot in current region: either wait for spot (cheap) or fall back to on-demand.
        # Waiting one step is safe if after losing one gap, we can still start on-demand and finish.
        # Conservative: assume we will pay restart overhead when starting on-demand later.
        can_wait_one_step = time_left >= (remaining_work + self._restart_overhead_s + self._gap + self._eps)

        if can_wait_one_step:
            # Optional multi-region hunt while waiting to increase chance of spot next step.
            # Only do this while waiting to avoid extra overhead during productive work.
            self._hunt_region_if_waiting()
            return CT_NONE

        return CT_OD