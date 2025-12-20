import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "my_strategy"  # REQUIRED: unique identifier

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the solution from spec_path config.

        The spec file contains:
        - deadline: deadline in hours
        - duration: task duration in hours
        - overhead: restart overhead in hours
        - trace_files: list of trace file paths (one per region)
        """
        with open(spec_path) as f:
            config = json.load(f)

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
            trace_files=config.get("trace_files", []),
        )
        super().__init__(args)

        # Cache key parameters in seconds.
        task_duration = getattr(self, "task_duration", 0.0)
        if isinstance(task_duration, (list, tuple)):
            self._total_task_duration = float(task_duration[0])
        else:
            self._total_task_duration = float(task_duration)

        self._deadline = float(getattr(self, "deadline", 0.0))
        self._restart_overhead = float(getattr(self, "restart_overhead", 0.0))

        env = getattr(self, "env", None)
        if env is not None:
            self._gap_seconds = float(getattr(env, "gap_seconds", 0.0))
        else:
            self._gap_seconds = 0.0

        # Internal state.
        self.committed_on_demand = False
        self.preferred_region = 0
        self._region_selected = False
        self._cumulative_done = 0.0
        self._last_segment_idx = 0

        # Choose preferred region using offline trace statistics (best average availability).
        trace_files = config.get("trace_files")
        if isinstance(trace_files, list) and trace_files:
            best_idx = 0
            best_score = -1.0
            for idx, path in enumerate(trace_files):
                try:
                    avail = 0
                    total = 0
                    with open(path) as tf:
                        for line in tf:
                            line = line.strip()
                            if not line:
                                continue
                            c = line[0]
                            if c in ("0", "1"):
                                total += 1
                                if c == "1":
                                    avail += 1
                            else:
                                parts = line.split(",")
                                if not parts:
                                    continue
                                v = parts[0].strip()
                                if v in ("0", "1"):
                                    total += 1
                                    if v == "1":
                                        avail += 1
                    if total > 0:
                        score = avail / total
                        if score > best_score:
                            best_score = score
                            best_idx = idx
                except Exception:
                    # Ignore any issues with reading/parsing trace files.
                    continue
            self.preferred_region = best_idx

        return self

    def _update_cumulative_work(self) -> None:
        """Incrementally update the total task work completed."""
        start_idx = self._last_segment_idx
        tdt = self.task_done_time
        current_len = len(tdt)
        if current_len > start_idx:
            total_add = 0.0
            for i in range(start_idx, current_len):
                total_add += tdt[i]
            self._cumulative_done += total_add
            self._last_segment_idx = current_len

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.

        Returns: ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        # Select preferred region once at the beginning (best average spot availability).
        if not self._region_selected:
            self._region_selected = True
            try:
                env = self.env
                current_region = env.get_current_region()
                target = self.preferred_region
                num_regions = env.get_num_regions()
                if isinstance(num_regions, int) and num_regions > 0:
                    target = target % num_regions
                if target != current_region:
                    try:
                        env.switch_region(target)
                    except Exception:
                        # If switching fails for any reason, just stay in current region.
                        pass
            except Exception:
                # If region operations are unavailable, ignore multi-region behavior.
                pass

        # Update work completed so far.
        self._update_cumulative_work()
        remaining_work = self._total_task_duration - self._cumulative_done

        # If task is complete, avoid further costs.
        if remaining_work <= 0.0:
            self.committed_on_demand = True
            return ClusterType.NONE

        env = self.env
        elapsed = env.elapsed_seconds
        time_left = self._deadline - elapsed

        # If already at/past deadline, just use on-demand to progress as much as possible.
        if time_left <= 0.0:
            self.committed_on_demand = True
            return ClusterType.ON_DEMAND

        gap = self._gap_seconds
        if gap <= 0.0:
            # Degenerate configuration; safest is to always use on-demand.
            self.committed_on_demand = True
            return ClusterType.ON_DEMAND

        # Once committed to on-demand, never return to spot.
        if self.committed_on_demand:
            return ClusterType.ON_DEMAND

        # Overhead required when we eventually switch to on-demand.
        overhead_future = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else self._restart_overhead

        # Safe to spend one more cheap timestep (SPOT or NONE) iff,
        # after potentially wasting a full step with zero progress,
        # we can still finish entirely on on-demand before the deadline.
        safe_to_wait = time_left >= (remaining_work + overhead_future + gap)

        if not safe_to_wait:
            # Not enough slack to risk spot/idle any further; commit to on-demand.
            self.committed_on_demand = True
            return ClusterType.ON_DEMAND

        # Plenty of slack remains: prefer cheap SPOT when available, else wait (NONE).
        if has_spot:
            return ClusterType.SPOT
        return ClusterType.NONE
