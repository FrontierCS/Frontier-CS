import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy with hard-deadline guarantee."""

    NAME = "cant_be_late_mr_v1"

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

        # Use our own cached copies of key parameters in seconds.
        self._deadline = float(config["deadline"]) * 3600.0
        self._task_duration = float(config["duration"]) * 3600.0
        self._restart_overhead = float(config["overhead"]) * 3600.0

        # Internal state for efficient tracking of completed work.
        self._work_done = 0.0
        self._task_done_idx = 0

        # Whether we've irrevocably committed to on-demand.
        self._committed_to_od = False

        # Optional flag for clarity; not strictly needed.
        self._job_done = False

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Incrementally update total work done.
        lst = self.task_done_time
        idx = self._task_done_idx
        if idx < len(lst):
            added = 0.0
            for i in range(idx, len(lst)):
                added += lst[i]
            self._work_done += added
            self._task_done_idx = len(lst)

        remaining_work = self._task_duration - self._work_done
        if remaining_work <= 1e-6:
            self._job_done = True
            return ClusterType.NONE

        elapsed = self.env.elapsed_seconds
        remaining_time = self._deadline - elapsed

        if remaining_time <= 0.0:
            # Past deadline; still try to finish as fast as possible.
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        # Commit to on-demand if slack is small enough that we must avoid
        # further non-progress. Add one gap as safety for discrete steps.
        if not self._committed_to_od:
            t_needed_od = self._restart_overhead + remaining_work
            gap = self.env.gap_seconds
            if remaining_time <= t_needed_od + gap:
                self._committed_to_od = True

        if self._committed_to_od:
            return ClusterType.ON_DEMAND

        # Before commit: prefer Spot when available; otherwise idle to save cost.
        if has_spot:
            return ClusterType.SPOT
        else:
            return ClusterType.NONE