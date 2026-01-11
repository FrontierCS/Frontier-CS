import json
from argparse import Namespace
from collections.abc import Sequence

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
        )
        super().__init__(args)

        # Normalize task_duration and restart_overhead to single float (seconds).
        td = getattr(self, "task_duration", None)
        if isinstance(td, (list, tuple)):
            self.task_duration = float(td[0])
        ro = getattr(self, "restart_overhead", None)
        if isinstance(ro, (list, tuple)):
            self.restart_overhead = float(ro[0])

        # Env attributes
        gap = float(getattr(self.env, "gap_seconds", 0.0))
        restart_overhead = float(getattr(self, "restart_overhead", 0.0))

        # Slack threshold: choose slightly larger than worst-case slack drop per step
        # (gap + restart_overhead) to guarantee committing before it's too late.
        self._slack_threshold = gap + restart_overhead

        # Multi-region info
        try:
            self._num_regions = int(self.env.get_num_regions())
        except Exception:
            self._num_regions = 1

        # Running totals for efficient progress tracking
        self._total_work_done = 0.0
        self._last_task_done_len = 0

        # On-demand commitment flag
        self._commit_to_on_demand = False

        # Region statistics (used when per-region spot availability is provided)
        self._region_total_steps = [0] * self._num_regions
        self._region_spot_steps = [0] * self._num_regions

        # Preferred region (not heavily used, but initialized for completeness)
        try:
            self._preferred_region = self.env.get_current_region()
        except Exception:
            self._preferred_region = 0

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot) -> ClusterType:
        """
        Decide next action based on current state.

        Returns: ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        # Update accumulated work efficiently (only new segments).
        tdt = self.task_done_time
        prev_len = self._last_task_done_len
        cur_len = len(tdt)
        if cur_len > prev_len:
            new_work = 0.0
            for v in tdt[prev_len:cur_len]:
                new_work += v
            self._total_work_done += new_work
            self._last_task_done_len = cur_len

        # If task already completed, no need to run further.
        if self._total_work_done >= self.task_duration - 1e-6:
            return ClusterType.NONE

        # Determine if has_spot is per-region sequence or single bool.
        is_vector = isinstance(has_spot, Sequence) and not isinstance(
            has_spot, (str, bytes)
        )

        # Update per-region spot statistics if vector is provided.
        if is_vector:
            hs = has_spot
            limit = min(self._num_regions, len(hs))
            for i in range(limit):
                self._region_total_steps[i] += 1
                if hs[i]:
                    self._region_spot_steps[i] += 1

        remaining_work = self.task_duration - self._total_work_done
        if remaining_work < 0.0:
            remaining_work = 0.0

        elapsed = float(self.env.elapsed_seconds)

        # If we've already committed to on-demand, always keep using it.
        if self._commit_to_on_demand:
            return ClusterType.ON_DEMAND

        # Compute earliest finish time if we commit to on-demand now.
        # If we're already on on-demand, no new restart overhead is incurred.
        if last_cluster_type == ClusterType.ON_DEMAND:
            overhead_for_commit = 0.0
        else:
            overhead_for_commit = float(self.restart_overhead)

        earliest_finish_time = elapsed + overhead_for_commit + remaining_work
        slack = float(self.deadline) - earliest_finish_time

        # Commit to on-demand when slack becomes small enough that delaying further
        # risks missing the deadline.
        if slack <= self._slack_threshold:
            self._commit_to_on_demand = True
            return ClusterType.ON_DEMAND

        # Not yet committed: prefer spot, fall back to idling when safe.
        if is_vector:
            hs = has_spot
            try:
                current_region = self.env.get_current_region()
            except Exception:
                current_region = 0

            limit = min(self._num_regions, len(hs))

            # Check if any region currently has spot.
            any_spot_available = False
            for i in range(limit):
                if hs[i]:
                    any_spot_available = True
                    break

            if any_spot_available:
                # Prefer staying in current region if it has spot.
                target_region = current_region
                if current_region >= limit or not hs[current_region]:
                    # Choose the region with spot and highest historical availability.
                    best_idx = None
                    best_score = -1.0
                    for i in range(limit):
                        if not hs[i]:
                            continue
                        total = self._region_total_steps[i]
                        spot = self._region_spot_steps[i]
                        score = float(spot) / total if total > 0 else 0.0
                        if score > best_score:
                            best_score = score
                            best_idx = i
                    if best_idx is None:
                        for i in range(limit):
                            if hs[i]:
                                best_idx = i
                                break
                    if best_idx is not None and best_idx != current_region:
                        try:
                            self.env.switch_region(best_idx)
                        except Exception:
                            pass
                        target_region = best_idx

                # Run on spot in the chosen region.
                # We know hs[target_region] was True at decision time.
                return ClusterType.SPOT
            else:
                # No spot anywhere, safely idle while we still have slack.
                return ClusterType.NONE
        else:
            # Single-region (or global) availability boolean.
            if bool(has_spot):
                return ClusterType.SPOT
            else:
                # Spot is unavailable; idle until we must switch to on-demand.
                return ClusterType.NONE