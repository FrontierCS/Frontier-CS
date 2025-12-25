from typing import Any, Optional, List, Tuple
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "safe_hedged_deadline"

    def __init__(self, args: Optional[Any] = None):
        super().__init__(args)
        self.args = args
        self.committed_to_od: bool = False
        self._cache_reset()

    def _cache_reset(self):
        self._cached_done_sum: float = 0.0
        self._cached_len: int = 0
        self._last_env_start_seen: float = -1.0

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _get_work_done(self) -> float:
        tdt = self.task_done_time
        if tdt is None:
            return 0.0
        try:
            current_len = len(tdt)
        except TypeError:
            # Not iterable, try to cast directly
            try:
                return float(tdt)
            except Exception:
                return 0.0

        # Detect reset/new run by non-monotonic progression in elapsed_seconds
        # or if list length decreased.
        if self.env is not None:
            if self.env.elapsed_seconds is not None:
                if self._last_env_start_seen > self.env.elapsed_seconds:
                    # New environment/run started
                    self._cache_reset()
                self._last_env_start_seen = self.env.elapsed_seconds

        if current_len < self._cached_len:
            # List was replaced/trimmed; recompute
            self._cached_done_sum = 0.0
            self._cached_len = 0

        # Incrementally add new segments
        for i in range(self._cached_len, current_len):
            seg = tdt[i]
            try:
                if isinstance(seg, (tuple, list)):
                    if len(seg) == 2:
                        a, b = seg
                        val = float(b) - float(a)
                        if val > 0:
                            self._cached_done_sum += val
                    else:
                        # Unsupported structure; try to sum contents
                        try:
                            self._cached_done_sum += sum(float(x) for x in seg)  # type: ignore
                        except Exception:
                            pass
                elif isinstance(seg, (int, float)):
                    self._cached_done_sum += float(seg)
                else:
                    # Try generic 'duration' attribute
                    try:
                        self._cached_done_sum += float(getattr(seg, "duration", 0.0))  # type: ignore
                    except Exception:
                        pass
            except Exception:
                # Ignore malformed entries
                pass

        self._cached_len = current_len
        return max(0.0, min(float(self.task_duration), self._cached_done_sum))

    def _remaining_work_seconds(self) -> float:
        done = self._get_work_done()
        rem = float(self.task_duration) - float(done)
        if rem < 0:
            rem = 0.0
        return rem

    def _commit_margin_seconds(self, gap: float) -> float:
        # Margin to safely wait an additional step considering discrete time.
        # One step margin is sufficient for worst-case no-progress over the next step.
        return float(gap)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Detect fresh run start: reset commitment and caches if at time 0
        try:
            if self.env.elapsed_seconds == 0:
                self.committed_to_od = False
                self._cache_reset()
        except Exception:
            pass

        # If already committed to On-Demand, stay there
        if self.committed_to_od or last_cluster_type == ClusterType.ON_DEMAND:
            self.committed_to_od = True
            return ClusterType.ON_DEMAND

        remaining_work = self._remaining_work_seconds()
        if remaining_work <= 0.0:
            return ClusterType.NONE

        elapsed = float(self.env.elapsed_seconds)
        deadline = float(self.deadline)
        gap = float(self.env.gap_seconds)
        time_remaining = max(0.0, deadline - elapsed)

        # Safety check: can we afford to wait one more step (possibly with zero progress)
        margin = self._commit_margin_seconds(gap)
        safe_to_wait = (time_remaining - (remaining_work + float(self.restart_overhead))) > margin

        if not safe_to_wait:
            # Commit to On-Demand to ensure completion
            self.committed_to_od = True
            return ClusterType.ON_DEMAND

        # Safe to wait: prefer Spot if available; otherwise pause
        if has_spot:
            return ClusterType.SPOT
        else:
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)