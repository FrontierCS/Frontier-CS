from typing import Any, Optional, List, Tuple, Dict
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_guard"

    def __init__(self, args=None):
        super().__init__(args)
        self.locked_to_od = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _sum_done(self) -> float:
        done = 0.0
        seq = getattr(self, "task_done_time", [])
        try:
            for seg in seq:
                if isinstance(seg, dict):
                    if "duration" in seg:
                        done += float(seg["duration"])
                    elif "end" in seg and "start" in seg:
                        done += float(seg["end"]) - float(seg["start"])
                    else:
                        try:
                            done += float(seg)
                        except Exception:
                            pass
                elif isinstance(seg, (list, tuple)):
                    try:
                        if len(seg) >= 2:
                            done += float(seg[1]) - float(seg[0])
                        elif len(seg) == 1:
                            done += float(seg[0])
                        else:
                            pass
                    except Exception:
                        for v in seg:
                            try:
                                done += float(v)
                            except Exception:
                                pass
                else:
                    try:
                        done += float(seg)
                    except Exception:
                        pass
        except Exception:
            try:
                done = float(sum(seq))
            except Exception:
                done = 0.0
        # Clamp to valid range
        try:
            total = float(self.task_duration)
        except Exception:
            total = done
        if total > 0:
            done = max(0.0, min(done, total))
        else:
            done = max(0.0, done)
        return done

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Remaining work
        total = float(self.task_duration)
        done = self._sum_done()
        remaining = max(0.0, total - done)

        if remaining <= 0.0:
            return ClusterType.NONE

        # Time parameters
        now = float(self.env.elapsed_seconds)
        deadline = float(self.deadline)
        dt = float(self.env.gap_seconds)
        slack = max(0.0, deadline - now)
        overhead = float(self.restart_overhead)

        # If already committed to OD, stay there
        if self.locked_to_od or last_cluster_type == ClusterType.ON_DEMAND:
            self.locked_to_od = True
            return ClusterType.ON_DEMAND

        # If not enough slack to finish with OD from now (considering switch overhead), switch to OD now
        overhead_to_od_now = overhead  # since we are not on OD at this moment
        if slack <= overhead_to_od_now + remaining:
            self.locked_to_od = True
            return ClusterType.ON_DEMAND

        # Prefer SPOT when safe; otherwise NONE if we can still wait; else OD
        if has_spot:
            if last_cluster_type == ClusterType.SPOT:
                # Safe to spend one more SPOT step if, after this step, we could still switch to OD and finish
                remaining_after = max(0.0, remaining - dt)
                slack_after = max(0.0, slack - dt)
                if slack_after >= overhead + remaining_after:
                    return ClusterType.SPOT
                else:
                    self.locked_to_od = True
                    return ClusterType.ON_DEMAND
            else:
                # Starting SPOT now may incur overhead; treat this step conservatively as no progress
                slack_after = max(0.0, slack - dt)
                if slack_after >= overhead + remaining:
                    return ClusterType.SPOT
                else:
                    self.locked_to_od = True
                    return ClusterType.ON_DEMAND
        else:
            # No SPOT available: wait if safe, otherwise switch to OD
            slack_after = max(0.0, slack - dt)
            if slack_after >= overhead + remaining:
                return ClusterType.NONE
            else:
                self.locked_to_od = True
                return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)