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

        self._task_done_idx: int = 0
        self._work_done: float = 0.0

        self._obs: Optional[List[int]] = None
        self._avail: Optional[List[int]] = None

        self._no_spot_streak: int = 0
        self._idle_no_spot_streak: int = 0
        self._committed_od: bool = False

        return self

    def _ensure_region_stats(self) -> None:
        n = self.env.get_num_regions()
        if self._obs is None or len(self._obs) != n:
            self._obs = [0] * n
            self._avail = [0] * n

    def _update_work_done(self) -> None:
        td = self.task_done_time
        i = self._task_done_idx
        if i >= len(td):
            return
        s = 0.0
        for j in range(i, len(td)):
            s += td[j]
        self._work_done += s
        self._task_done_idx = len(td)

    def _posterior_mean(self, idx: int) -> float:
        # Laplace smoothing
        a = self._avail[idx] + 1
        b = self._obs[idx] + 2
        return a / b

    def _best_region(self, cur: int) -> int:
        n = self.env.get_num_regions()
        best = cur
        best_score = self._posterior_mean(cur)
        for i in range(n):
            if i == cur:
                continue
            s = self._posterior_mean(i)
            if s > best_score:
                best_score = s
                best = i
        return best

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._update_work_done()

        remain_work = self.task_duration - self._work_done
        if remain_work <= 0:
            return ClusterType.NONE

        t = self.env.elapsed_seconds
        remain_time = self.deadline - t
        gap = float(self.env.gap_seconds)
        ro = float(self.restart_overhead)

        # If already too late (shouldn't happen), run on-demand.
        if remain_time <= 0:
            return ClusterType.ON_DEMAND

        slack = remain_time - remain_work

        # Hard safety: commit to on-demand when very close to the feasibility boundary.
        must_buffer = 0.5 * gap
        if slack <= ro + must_buffer:
            self._committed_od = True
        if self._committed_od:
            return ClusterType.ON_DEMAND

        self._ensure_region_stats()
        cur = self.env.get_current_region()

        self._obs[cur] += 1
        if has_spot:
            self._avail[cur] += 1
            self._no_spot_streak = 0
            self._idle_no_spot_streak = 0
        else:
            self._no_spot_streak += 1

        n_regions = self.env.get_num_regions()
        if n_regions > 1 and not has_spot:
            # If spot is down for a bit, relocate (while not risking choosing spot blindly).
            # Only do this when we still have comfortable slack so extra overhead won't jeopardize.
            switch_streak = 2
            if self._no_spot_streak >= switch_streak and slack >= 3.0 * gap:
                target = self._best_region(cur)
                if target != cur:
                    self.env.switch_region(target)
                    self._no_spot_streak = 0
                    cur = target

        if has_spot:
            if last_cluster_type == ClusterType.ON_DEMAND:
                # Switch back only if it's likely worth paying a restart overhead.
                if remain_work >= 3.0 * gap and slack >= (ro + 1.5 * gap):
                    return ClusterType.SPOT
                return ClusterType.ON_DEMAND
            return ClusterType.SPOT

        # No spot available here this step.
        # Decide between waiting (free) and on-demand (expensive) based on slack and how long we've waited.
        # Allow more waiting when slack is large, but cap to avoid pathological long outages.
        if slack >= 2.5 * gap:
            max_idle_steps = int(min(6.0, max(1.0, (slack - (ro + gap)) / gap)))
            if self._idle_no_spot_streak < max_idle_steps:
                self._idle_no_spot_streak += 1
                return ClusterType.NONE

        self._idle_no_spot_streak = 0
        return ClusterType.ON_DEMAND
