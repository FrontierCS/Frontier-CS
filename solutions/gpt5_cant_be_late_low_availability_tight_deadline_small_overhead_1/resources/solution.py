from typing import Any, List, Union

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "deadline_backup_od"

    def __init__(self, args=None):
        super().__init__(args)
        self._committed_to_od = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _sum_done_seconds(self) -> float:
        td = getattr(self, "task_done_time", None)
        if not td:
            return 0.0
        total = 0.0
        try:
            for seg in td:
                if seg is None:
                    continue
                if isinstance(seg, (int, float)):
                    total += float(seg)
                elif isinstance(seg, dict):
                    if "duration" in seg:
                        total += float(seg.get("duration", 0.0))
                    elif "start" in seg and "end" in seg:
                        total += float(seg["end"]) - float(seg["start"])
                elif isinstance(seg, (list, tuple)):
                    if len(seg) >= 2:
                        total += float(seg[1]) - float(seg[0])
                else:
                    # Fallback for objects with attributes
                    if hasattr(seg, "duration"):
                        total += float(getattr(seg, "duration"))
                    elif hasattr(seg, "start") and hasattr(seg, "end"):
                        total += float(getattr(seg, "end")) - float(getattr(seg, "start"))
        except Exception:
            # Be robust to any unexpected segment formats
            pass
        return max(0.0, total)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        done = self._sum_done_seconds()
        remaining_work = max(0.0, float(self.task_duration) - done)
        if remaining_work <= 1e-9:
            self._committed_to_od = False
            return ClusterType.NONE

        time_left = float(self.deadline) - float(self.env.elapsed_seconds)
        if time_left <= 0:
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        # Guard buffer to handle discrete step effects
        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        guard = gap if gap > 1e-6 else 1.0

        # Commit to on-demand if we are at/near the latest safe start time
        if not self._committed_to_od:
            if time_left <= remaining_work + float(self.restart_overhead) + guard:
                self._committed_to_od = True

        if self._committed_to_od:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
