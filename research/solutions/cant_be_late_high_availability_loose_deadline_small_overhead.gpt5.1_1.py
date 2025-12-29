from typing import Any
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_threshold_v1"

    def __init__(self, args: Any = None):
        super().__init__(args)
        self.committed_to_od = False
        self._prog_mode = "unset"  # "unset", "durations", "segments", "unknown"
        self._prog_index = 0
        self._prog_value = 0.0

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _estimate_progress(self) -> float:
        """Estimate completed work time in seconds, conservative (never overestimates)."""
        segs = getattr(self, "task_done_time", None)
        if not segs:
            return 0.0

        elapsed = getattr(self.env, "elapsed_seconds", 0.0)
        total_duration = getattr(self, "task_duration", float("inf"))

        # Determine representation mode on first use
        if self._prog_mode == "unset":
            first = segs[0]
            if isinstance(first, (int, float)):
                self._prog_mode = "durations"
            elif (
                isinstance(first, (list, tuple))
                and len(first) >= 2
                and isinstance(first[0], (int, float))
                and isinstance(first[1], (int, float))
            ):
                self._prog_mode = "segments"
            else:
                # Unknown structure; fall back to conservative "no progress"
                self._prog_mode = "unknown"
                self._prog_index = len(segs)
                self._prog_value = 0.0
                return 0.0

        if self._prog_mode == "durations":
            n = len(segs)
            for i in range(self._prog_index, n):
                v = segs[i]
                if isinstance(v, (int, float)):
                    self._prog_value += float(v)
            self._prog_index = n
            # If representation is suspicious (more work than time), fall back to 0
            if self._prog_value > elapsed + 1e-6:
                self._prog_mode = "unknown"
                self._prog_value = 0.0
                return 0.0

        elif self._prog_mode == "segments":
            n = len(segs)
            for i in range(self._prog_index, n):
                seg = segs[i]
                try:
                    start = float(seg[0])
                    end = float(seg[1])
                except Exception:
                    continue
                if end > start:
                    self._prog_value += end - start
            self._prog_index = n
            if self._prog_value > elapsed + 1e-6:
                self._prog_mode = "unknown"
                self._prog_value = 0.0
                return 0.0
        else:  # "unknown"
            return 0.0

        done = self._prog_value
        if done < 0.0:
            done = 0.0
        if done > elapsed:
            done = elapsed
        if done > total_duration:
            done = total_duration
        return done

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Estimate how much work is already done
        done = self._estimate_progress()
        remaining = self.task_duration - done
        if remaining <= 0:
            return ClusterType.NONE

        elapsed = self.env.elapsed_seconds
        gap = getattr(self.env, "gap_seconds", 0.0) or 0.0
        deadline = self.deadline
        restart_overhead = self.restart_overhead

        # Time (in worst case) to finish if we commit to on-demand starting now
        # Includes one restart overhead to be conservative.
        worst_finish_if_start_now = elapsed + remaining + restart_overhead

        # Decide whether to irrevocably commit to on-demand
        if not self.committed_to_od:
            # It is unsafe to delay on-demand by another gap if, in the worst
            # case of 0 work during that gap, starting OD afterwards would miss
            # the deadline. So if:
            #   elapsed + remaining + overhead > deadline - gap
            # we must start OD now.
            latest_safe_finish_after_wait = deadline - gap
            if worst_finish_if_start_now > latest_safe_finish_after_wait:
                self.committed_to_od = True

        if self.committed_to_od:
            return ClusterType.ON_DEMAND

        # Not yet committed: use spot whenever available, otherwise wait.
        if has_spot:
            return ClusterType.SPOT
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)