import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy with deadline guarantee and cost awareness."""

    NAME = "cant_be_late_multiregion_v1"

    def solve(self, spec_path: str) -> "Solution":
        """Initialize the solution from spec_path config."""
        with open(spec_path) as f:
            config = json.load(f)

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)

        # Internal tracking of completed work (seconds).
        self._progress = 0.0
        self._known_done_segments = 0
        self._committed_on_demand = False

        # Safety margin to handle discrete steps and overhead.
        gap = getattr(self.env, "gap_seconds", 0.0) or 0.0
        restart_overhead = getattr(self, "restart_overhead", 0.0) or 0.0
        # Require margin >= gap to avoid missing deadline due to discretization.
        self._safety_margin = max(gap, restart_overhead)

        # Optional: pick a preferred region based on trace_files, if available.
        self._preferred_region = 0
        trace_files = config.get("trace_files") or []
        try:
            num_regions = self.env.get_num_regions()
        except Exception:
            num_regions = None

        if trace_files and num_regions:
            best_idx = 0
            best_score = -1.0
            for i, path in enumerate(trace_files):
                if i >= num_regions:
                    break
                score = -1.0
                try:
                    with open(path, "r") as tf:
                        # Limit read size to avoid huge memory usage.
                        data = tf.read(4 * 1024 * 1024)
                    if data:
                        ones = data.count("1")
                        zeros = data.count("0")
                        total = ones + zeros
                        if total > 0:
                            score = ones / float(total)
                        else:
                            lower = data.lower()
                            trues = lower.count("true")
                            falses = lower.count("false")
                            total_tf = trues + falses
                            if total_tf > 0:
                                score = trues / float(total_tf)
                            else:
                                score = -1.0
                except Exception:
                    score = -1.0
                if score > best_score:
                    best_score = score
                    best_idx = i
            self._preferred_region = best_idx
            try:
                current_region = self.env.get_current_region()
            except Exception:
                current_region = None
            if current_region is not None and self._preferred_region != current_region:
                try:
                    self.env.switch_region(self._preferred_region)
                except Exception:
                    pass

        return self

    def _update_progress(self) -> None:
        """Incrementally update internal progress based on task_done_time."""
        segments = getattr(self, "task_done_time", None)
        if not isinstance(segments, list):
            return
        k = self._known_done_segments
        if k >= len(segments):
            return
        try:
            new_sum = 0.0
            for v in segments[k:]:
                try:
                    new_sum += float(v)
                except Exception:
                    continue
            self._progress += new_sum
            self._known_done_segments = len(segments)
        except Exception:
            try:
                self._progress = float(sum(float(x) for x in segments))
                self._known_done_segments = len(segments)
            except Exception:
                pass

    def _get_task_duration(self) -> float:
        """Return task duration (seconds) as a scalar."""
        td = getattr(self, "task_duration", None)
        if isinstance(td, (list, tuple)):
            if td:
                try:
                    return float(td[0])
                except Exception:
                    return 0.0
            return 0.0
        if td is None:
            return 0.0
        try:
            return float(td)
        except Exception:
            return 0.0

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.

        Returns: ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        # Update internal progress accounting.
        self._update_progress()

        total_needed = self._get_task_duration()
        remaining = total_needed - self._progress
        if remaining <= 0:
            # Task already completed; no need to run further.
            self._committed_on_demand = True
            return ClusterType.NONE

        current_time = getattr(self.env, "elapsed_seconds", 0.0) or 0.0
        deadline = getattr(self, "deadline", current_time) or current_time
        time_left = deadline - current_time

        if time_left <= 0:
            # Past deadline; just use on-demand to minimize additional delay.
            self._committed_on_demand = True
            return ClusterType.ON_DEMAND

        # Decide whether it's time to commit to on-demand to guarantee completion.
        if not self._committed_on_demand:
            restart_overhead = getattr(self, "restart_overhead", 0.0) or 0.0
            # Worst-case time needed if we switch to on-demand now and run continuously.
            time_needed = remaining + restart_overhead + (self._safety_margin or 0.0)
            if time_left <= time_needed:
                self._committed_on_demand = True

        if self._committed_on_demand:
            # Once committed, stay on on-demand until completion, ignoring spot.
            return ClusterType.ON_DEMAND

        # Before commitment: prefer spot when available; otherwise idle to save cost.
        if has_spot:
            return ClusterType.SPOT

        return ClusterType.NONE
