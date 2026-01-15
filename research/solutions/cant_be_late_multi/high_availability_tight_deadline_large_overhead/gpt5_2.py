import json
from argparse import Namespace
from typing import Optional

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_mr"

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
        self.committed_on_demand = False
        self._region_seen = None
        self._region_spot = None
        self._region_cursor = 0
        return self

    def _ensure_region_stats(self):
        try:
            n = self.env.get_num_regions()
        except Exception:
            n = 0
        if n > 0 and (self._region_seen is None or len(self._region_seen) != n):
            self._region_seen = [0] * n
            self._region_spot = [0] * n
            self._region_cursor = 0

    def _update_region_stats(self, has_spot: bool):
        try:
            idx = self.env.get_current_region()
        except Exception:
            return
        if self._region_seen is None:
            return
        if 0 <= idx < len(self._region_seen):
            self._region_seen[idx] += 1
            if has_spot:
                self._region_spot[idx] += 1

    def _pick_next_region(self, exclude_idx: Optional[int] = None) -> int:
        n = self.env.get_num_regions()
        if n <= 1:
            return 0
        if self._region_seen is None or len(self._region_seen) != n:
            self._ensure_region_stats()
        total_seen = sum(self._region_seen) if self._region_seen else 0
        current = self.env.get_current_region()
        if total_seen < 2 * n:
            idx = (current + 1) % n
            if exclude_idx is not None and idx == exclude_idx:
                idx = (idx + 1) % n
            return idx
        best_idx = current
        best_score = -1.0
        for i in range(n):
            if exclude_idx is not None and i == exclude_idx:
                continue
            seen = self._region_seen[i]
            spot = self._region_spot[i]
            score = (spot + 1.0) / (seen + 2.0)
            if score > best_score or (score == best_score and i != current and i < best_idx):
                best_score = score
                best_idx = i
        if best_idx == current and n > 1:
            return (current + 1) % n
        return best_idx

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_region_stats()
        self._update_region_stats(has_spot)

        gap = float(getattr(self.env, "gap_seconds", 0.0))
        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0))
        deadline = float(self.deadline)
        time_left = max(deadline - elapsed, 0.0)

        total = float(self.task_duration)
        done = float(sum(self.task_done_time)) if hasattr(self, "task_done_time") else 0.0
        remain = max(total - done, 0.0)

        if remain <= 0.0:
            return ClusterType.NONE

        H = float(self.restart_overhead)

        if self.committed_on_demand:
            return ClusterType.ON_DEMAND

        if time_left <= remain + H:
            self.committed_on_demand = True
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        if time_left >= remain + H + gap:
            try:
                n = self.env.get_num_regions()
                if n and n > 1:
                    new_idx = self._pick_next_region(exclude_idx=self.env.get_current_region())
                    if isinstance(new_idx, int) and 0 <= new_idx < n and new_idx != self.env.get_current_region():
                        self.env.switch_region(new_idx)
            except Exception:
                pass
            return ClusterType.NONE

        self.committed_on_demand = True
        return ClusterType.ON_DEMAND