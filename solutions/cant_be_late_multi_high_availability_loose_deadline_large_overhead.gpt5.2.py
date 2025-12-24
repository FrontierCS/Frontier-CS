import json
import math
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_ucb"

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

        self._done_seconds = 0.0
        self._done_idx = 0

        self._initialized = False
        self._up_obs = None
        self._tot_obs = None

        self._spot_down_streak = 0
        self._switch_cooldown = 0

        self._ondemand_mode = False
        self._ondemand_committed_at = None

        self._ct_none = getattr(ClusterType, "NONE", None)
        if self._ct_none is None:
            self._ct_none = getattr(ClusterType, "None", None)
        if self._ct_none is None:
            self._ct_none = ClusterType.NONE  # may raise early if enum differs

        return self

    @staticmethod
    def _scalar(x: object) -> float:
        if isinstance(x, (list, tuple)):
            return float(x[0])
        return float(x)

    def _update_done(self) -> None:
        td = self.task_done_time
        n = len(td)
        i = self._done_idx
        if i < n:
            s = 0.0
            while i < n:
                s += float(td[i])
                i += 1
            self._done_seconds += s
            self._done_idx = n

    def _maybe_init(self) -> None:
        if self._initialized:
            return
        try:
            nr = int(self.env.get_num_regions())
        except Exception:
            nr = 1
        self._up_obs = [0] * nr
        self._tot_obs = [0] * nr
        self._initialized = True

    def _safety_buffer(self) -> float:
        gap = float(self.env.gap_seconds)
        ro = float(self._scalar(self.restart_overhead))
        return max(2.0 * gap, 0.5 * ro)

    def _urgent(self, remaining_work: float, remaining_time: float) -> bool:
        ro = float(self._scalar(self.restart_overhead))
        buf = self._safety_buffer()
        return remaining_time <= (remaining_work + ro + buf)

    def _choose_region_ucb(self, exclude: int) -> int:
        nr = len(self._tot_obs)
        total = sum(self._tot_obs) + 1
        log_total = math.log(total + 1.0)
        c = 0.9
        best_idx = exclude
        best_score = -1e18
        for i in range(nr):
            if i == exclude:
                continue
            t = self._tot_obs[i]
            u = self._up_obs[i]
            mean = (u + 1.0) / (t + 2.0)
            bonus = c * math.sqrt(log_total / (t + 1.0))
            score = mean + bonus
            if score > best_score:
                best_score = score
                best_idx = i
        return best_idx

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._maybe_init()
        self._update_done()

        task_duration = float(self._scalar(self.task_duration))
        deadline = float(self._scalar(self.deadline))

        remaining_work = task_duration - self._done_seconds
        if remaining_work <= 0.0:
            return self._ct_none

        now = float(self.env.elapsed_seconds)
        remaining_time = deadline - now
        if remaining_time <= 0.0:
            return ClusterType.ON_DEMAND

        try:
            cur_region = int(self.env.get_current_region())
        except Exception:
            cur_region = 0

        if 0 <= cur_region < len(self._tot_obs):
            self._tot_obs[cur_region] += 1
            if has_spot:
                self._up_obs[cur_region] += 1

        if self._switch_cooldown > 0:
            self._switch_cooldown -= 1

        if not self._ondemand_mode and self._urgent(remaining_work, remaining_time):
            self._ondemand_mode = True
            self._ondemand_committed_at = now

        if self._ondemand_mode:
            return ClusterType.ON_DEMAND

        if has_spot:
            self._spot_down_streak = 0
            return ClusterType.SPOT

        self._spot_down_streak += 1

        nr = len(self._tot_obs)
        if nr > 1 and self._switch_cooldown == 0:
            gap = float(self.env.gap_seconds)
            ro = float(self._scalar(self.restart_overhead))
            min_cooldown = max(1, int(ro / max(gap, 1e-9)))
            if self._spot_down_streak >= 3:
                nxt = self._choose_region_ucb(exclude=cur_region)
                if nxt != cur_region:
                    try:
                        self.env.switch_region(nxt)
                    except Exception:
                        pass
                self._switch_cooldown = max(3, min_cooldown)
                self._spot_down_streak = 0

        return self._ct_none
