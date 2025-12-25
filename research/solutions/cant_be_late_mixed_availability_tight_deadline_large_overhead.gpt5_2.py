from typing import Any, Optional
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "deadline_commit_strategy_v1"

    def __init__(self, args: Optional[Any] = None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except Exception:
                pass
        self.args = args
        self._committed_to_od = False
        self._commit_time_recorded = None

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _progress_seconds(self) -> float:
        # Robustly sum accomplished work from task_done_time
        done = 0.0
        try:
            segments = self.task_done_time
        except AttributeError:
            return 0.0
        if not segments:
            return 0.0
        try:
            for seg in segments:
                if isinstance(seg, (int, float)):
                    done += float(seg)
                elif isinstance(seg, (list, tuple)):
                    if len(seg) >= 2:
                        try:
                            a = float(seg[0])
                            b = float(seg[1])
                            done += max(0.0, b - a)
                        except Exception:
                            continue
                # Ignore other types
        except Exception:
            # Fallback to best-effort
            try:
                done = float(sum(segments))
            except Exception:
                done = 0.0
        return max(0.0, min(done, float(self.task_duration)))

    def _should_commit_to_od(self, remaining_work: float, time_remaining: float) -> bool:
        # Fudge to handle discretization and strict deadline
        gap = getattr(self.env, "gap_seconds", 60.0) or 60.0
        fudge = max(1.0, gap)
        # If we are already on OD, no startup buffer required; else include restart overhead
        startup_buffer = 0.0 if self.env.cluster_type == ClusterType.ON_DEMAND else float(self.restart_overhead)
        # Commit when we must switch to OD to certainly finish before deadline
        return time_remaining <= remaining_work + startup_buffer + fudge

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If already committed to OD, stay there until completion
        progress = self._progress_seconds()
        remaining = max(0.0, float(self.task_duration) - progress)
        if remaining <= 0.0:
            return ClusterType.NONE

        elapsed = float(self.env.elapsed_seconds)
        deadline = float(self.deadline)
        time_remaining = max(0.0, deadline - elapsed)

        if self._committed_to_od:
            return ClusterType.ON_DEMAND

        # Decide whether to commit to OD now
        if self._should_commit_to_od(remaining, time_remaining):
            self._committed_to_od = True
            self._commit_time_recorded = elapsed
            return ClusterType.ON_DEMAND

        # Otherwise, prefer Spot when available; pause when not
        if has_spot:
            return ClusterType.SPOT
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        # Allow passthrough of unknown args
        args, _ = parser.parse_known_args()
        return cls(args)