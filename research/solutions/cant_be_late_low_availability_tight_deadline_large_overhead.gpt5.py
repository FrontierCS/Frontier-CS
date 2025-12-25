from typing import Any, List, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_heuristic_v1"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._lock_od: bool = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _get_done_seconds(self) -> float:
        done = 0.0
        segments = getattr(self, "task_done_time", []) or []
        for seg in segments:
            try:
                done += float(seg)
            except Exception:
                try:
                    if isinstance(seg, dict):
                        if "duration" in seg:
                            done += float(seg["duration"])
                        elif "end" in seg and "start" in seg:
                            done += float(seg["end"]) - float(seg["start"])
                except Exception:
                    continue
        return max(0.0, done)

    def _remaining_work_seconds(self) -> float:
        total = float(getattr(self, "task_duration", 0.0) or 0.0)
        done = self._get_done_seconds()
        return max(0.0, total - done)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If already committed to on-demand, stay on-demand
        if self._lock_od:
            return ClusterType.ON_DEMAND

        # Compute remaining work and commit time threshold
        now = float(self.env.elapsed_seconds)
        gap = float(self.env.gap_seconds)
        deadline = float(self.deadline)
        rem_work = self._remaining_work_seconds()

        if rem_work <= 0.0:
            return ClusterType.NONE

        overhead = float(self.restart_overhead)

        # Latest time at which starting OD (paying one restart overhead) guarantees finishing by deadline
        commit_time = deadline - (rem_work + overhead)

        # If the next step could push us beyond the commit boundary in the worst case (no progress),
        # we must commit to OD now unless we are already on SPOT and can safely make progress this step.
        must_commit_now = (now + gap) >= commit_time

        if must_commit_now:
            # If currently on SPOT and SPOT is available, running SPOT for this step is safe:
            # we will make progress this step (no preemption within step), and switching to OD next step
            # yields the same finish time as switching now.
            if has_spot and last_cluster_type == ClusterType.SPOT:
                return ClusterType.SPOT
            # Otherwise, commit to OD to guarantee finish
            self._lock_od = True
            return ClusterType.ON_DEMAND

        # Not yet at commit boundary: use SPOT when available, otherwise wait (NONE)
        if has_spot:
            return ClusterType.SPOT
        else:
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)