import math
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_heuristic_v2"

    def __init__(self, args=None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except Exception:
                pass
        self.args = args
        # Lazy init of runtime fields in _step

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Lazy initialization
        if not hasattr(self, "_initialized"):
            self._initialized = True
            self._lock_to_od = False
            self._spot_on_count = 0
            self._total_count = 0
            self._persist_od_until = None
            self._no_spot_start_time = None
            self._lock_threshold = None
            self._persist_min = None

        # Update spot availability history
        self._total_count += 1
        if has_spot:
            self._spot_on_count += 1

        # Environment parameters
        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        oh = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        tleft = deadline - elapsed

        # Compute work remaining
        done = 0.0
        try:
            if self.task_done_time:
                for seg in self.task_done_time:
                    try:
                        done += float(seg)
                    except Exception:
                        if isinstance(seg, (list, tuple)) and seg:
                            try:
                                done += float(seg[0])
                            except Exception:
                                pass
        except Exception:
            try:
                done = float(getattr(self, "total_done_seconds", 0.0))
            except Exception:
                done = 0.0

        total = float(getattr(self, "task_duration", 0.0) or 0.0)
        remain = max(total - done, 0.0)

        # If finished, stop spending
        if remain <= 1e-9:
            return ClusterType.NONE

        # Slack is how much idle time we can afford
        slack = tleft - remain

        # Initialize thresholds once gap/overhead known
        if self._lock_threshold is None:
            self._lock_threshold = max(0.0, oh + 2.0 * gap)
            self._persist_min = max(600.0, 2.0 * gap)

        # Track off streak start
        if has_spot:
            self._no_spot_start_time = None
        else:
            if self._no_spot_start_time is None:
                self._no_spot_start_time = elapsed

        # Hard lock to on-demand when slack is very low
        if not self._lock_to_od and slack <= self._lock_threshold + 0.25 * gap:
            self._lock_to_od = True
            self._persist_od_until = None

        if self._lock_to_od:
            return ClusterType.ON_DEMAND

        # Not locked: dynamic waiting policy when no spot
        p = (self._spot_on_count / self._total_count) if self._total_count > 0 else 0.5
        base_wait = 5400.0  # 1.5 hours
        var = (p - 0.5) * 7200.0  # +/-2 hours based on observed availability
        s0 = base_wait + var
        ratio_rem = (remain / total) if total > 0 else 1.0
        s0 += min(3600.0, 3600.0 * ratio_rem)  # add up to 1h earlier in the job

        # Clamp within [0.5h, 4h]
        s0 = max(1800.0, min(14400.0, s0))
        # Always keep at least a lock-threshold margin
        s0 = max(s0, self._lock_threshold + gap)

        # If we recently started OD (but not locked), persist shortly to avoid thrash
        if self._persist_od_until is not None and elapsed < self._persist_od_until:
            return ClusterType.ON_DEMAND
        else:
            self._persist_od_until = None

        if has_spot:
            return ClusterType.SPOT

        # No spot available: decide between waiting and OD
        off_streak = 0.0
        if self._no_spot_start_time is not None:
            off_streak = elapsed - self._no_spot_start_time

        dynamic_s0 = s0
        if off_streak > 0.5 * s0:
            dynamic_s0 = max(self._lock_threshold + gap, s0 * 0.75)
        if off_streak > s0:
            dynamic_s0 = self._lock_threshold + gap

        if slack > dynamic_s0:
            return ClusterType.NONE

        # Start OD and persist briefly
        self._persist_od_until = elapsed + self._persist_min
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)