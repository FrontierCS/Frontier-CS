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
        return self

    def _ensure_runtime_state(self) -> None:
        if getattr(self, "_rt_init", False):
            return
        self._rt_init = True
        try:
            n = int(self.env.get_num_regions())
        except Exception:
            n = 1
        self._n_regions = max(1, n)
        self._visits = [0] * self._n_regions
        self._avail = [0] * self._n_regions
        self._last_switch_step = -10**18
        self._switch_cooldown_steps = 5
        self._commit_ondemand = False
        self._done = 0.0
        self._last_done_len = 0

    def _update_done(self) -> float:
        td = self.task_done_time
        ln = len(td)
        if ln == self._last_done_len:
            return self._done
        if self._last_done_len == 0:
            s = 0.0
            for x in td:
                s += float(x)
            self._done = s
        else:
            s = self._done
            for i in range(self._last_done_len, ln):
                s += float(td[i])
            self._done = s
        self._last_done_len = ln
        if self._done < 0.0:
            self._done = 0.0
        return self._done

    def _step_idx(self, gap: float) -> int:
        if gap > 0:
            return int(self.env.elapsed_seconds // gap)
        return int(self.env.elapsed_seconds)

    def _choose_region_ucb(self) -> int:
        n = self._n_regions
        if n <= 1:
            return 0
        total = 0
        for v in self._visits:
            total += v
        logt = math.log(total + 2.0)

        best_r = 0
        best_score = -1e18
        for r in range(n):
            v = self._visits[r]
            if v <= 0:
                score = 1e9
            else:
                mean = self._avail[r] / v
                score = mean + math.sqrt(2.0 * logt / v)
            if score > best_score:
                best_score = score
                best_r = r
        return best_r

    def _should_switch_on_idle(self, step_idx: int, current_region: int) -> int:
        if self._n_regions <= 1:
            return current_region
        if step_idx - self._last_switch_step < self._switch_cooldown_steps:
            return current_region

        target = self._choose_region_ucb()
        if target == current_region:
            return current_region

        vc = self._visits[current_region]
        vt = self._visits[target]
        if vc >= 10 and vt >= 10:
            mc = self._avail[current_region] / max(1, vc)
            mt = self._avail[target] / max(1, vt)
            if mt - mc < 0.05:
                return current_region
        return target

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_runtime_state()

        gap = float(getattr(self.env, "gap_seconds", 1.0) or 1.0)
        step_idx = self._step_idx(gap)

        try:
            r = int(self.env.get_current_region())
        except Exception:
            r = 0
        if r < 0:
            r = 0
        elif r >= self._n_regions:
            r = self._n_regions - 1

        self._visits[r] += 1
        if bool(has_spot):
            self._avail[r] += 1

        done = self._update_done()
        task_dur = float(self.task_duration)
        if done >= task_dur - 1e-9:
            return ClusterType.NONE

        remaining_work = task_dur - done
        elapsed = float(self.env.elapsed_seconds)
        remaining_time = float(self.deadline) - elapsed

        pending = float(getattr(self, "remaining_restart_overhead", 0.0) or 0.0)
        if pending < 0.0:
            pending = 0.0

        if self._commit_ondemand:
            return ClusterType.ON_DEMAND

        if last_cluster_type == ClusterType.ON_DEMAND:
            need_overhead_if_ondemand = pending
        else:
            need_overhead_if_ondemand = float(self.restart_overhead)

        if remaining_time <= remaining_work + need_overhead_if_ondemand + 2.0 * gap:
            self._commit_ondemand = True
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        safe_to_idle = remaining_time > remaining_work + float(self.restart_overhead) + 3.0 * gap
        if safe_to_idle:
            target = self._should_switch_on_idle(step_idx, r)
            if target != r:
                try:
                    self.env.switch_region(int(target))
                    self._last_switch_step = step_idx
                except Exception:
                    pass
            return ClusterType.NONE

        self._commit_ondemand = True
        return ClusterType.ON_DEMAND