from typing import Any, List, Tuple
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_safespot_v1"

    def __init__(self, args: Any = None):
        super().__init__(args)
        self._committed_to_od = False
        self._last_elapsed = -1.0

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _reset_if_new_run(self):
        # Detect new run when elapsed time decreases (environment reset)
        if self._last_elapsed > self.env.elapsed_seconds:
            self._committed_to_od = False
        self._last_elapsed = self.env.elapsed_seconds

    def _compute_done_seconds(self) -> float:
        done = 0.0
        segments = getattr(self, "task_done_time", []) or []
        for seg in segments:
            if isinstance(seg, (list, tuple)) and len(seg) >= 2:
                try:
                    done += float(seg[1]) - float(seg[0])
                except Exception:
                    continue
            else:
                try:
                    done += float(seg)
                except Exception:
                    continue
        # Clamp to [0, task_duration]
        try:
            td = float(self.task_duration)
        except Exception:
            td = done
        if td >= 0:
            if done < 0:
                return 0.0
            if done > td:
                return td
        return done

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._reset_if_new_run()

        # Safety cushion to account for step granularity
        eps = max(float(getattr(self.env, "gap_seconds", 1.0)), 1.0)

        done = self._compute_done_seconds()
        try:
            task_duration = float(self.task_duration)
        except Exception:
            task_duration = done
        remaining = max(0.0, task_duration - done)

        # If task already completed, stop to avoid cost
        if remaining <= 0.0:
            self._committed_to_od = False
            return ClusterType.NONE

        # Time left until deadline
        try:
            deadline = float(self.deadline)
            now = float(self.env.elapsed_seconds)
        except Exception:
            # Fallback to conservative behavior: run on-demand
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        time_left = deadline - now

        # If past deadline, run OD (penalty likely unavoidable, but best effort)
        if time_left <= 0.0:
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        # Decide commitment threshold to guarantee completion
        try:
            restart_overhead = float(self.restart_overhead)
        except Exception:
            restart_overhead = 0.0

        # If already committed, stay on OD to avoid overhead and risk
        if self._committed_to_od:
            return ClusterType.ON_DEMAND

        # Overhead if we switch to OD now (0 if already OD, else restart_overhead)
        overhead_to_commit_now = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else restart_overhead

        # Check if we must commit now to safely finish on OD before deadline
        if time_left <= remaining + overhead_to_commit_now + eps:
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        # Opportunistic mode (not committed yet)
        if has_spot:
            # Use SPOT when available while it's still safe
            return ClusterType.SPOT

        # Spot is not available: wait if still safe, else commit to OD
        if time_left <= remaining + restart_overhead + eps:
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
