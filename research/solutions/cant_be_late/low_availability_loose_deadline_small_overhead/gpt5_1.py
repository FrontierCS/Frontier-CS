import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args=None):
        super().__init__(args)
        # Tunable parameters (defaults if args is None)
        self.commit_buffer_minutes = getattr(args, "commit_buffer_minutes", 10.0)
        self.switch_back_buffer_hours = getattr(args, "switch_back_buffer_hours", 2.0)

        # Internal state
        self._initialized = False
        self._done_cache_sum = 0.0
        self._done_cache_len = 0
        self._done_cache_list = None
        self._od_locked = False  # Once we commit to OD near deadline, never switch back

        # Computed buffers (initialized later when env is available)
        self._commit_buffer_seconds = None
        self._switch_back_buffer_seconds = None

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _init_if_needed(self):
        if not self._initialized:
            # Establish buffers with environment-aware floors
            gap = getattr(self.env, "gap_seconds", 300.0) or 300.0
            overhead = getattr(self, "restart_overhead", 0.0) or 0.0

            # Commit buffer: safety cushion to account for discretization/overhead
            # Use max of user setting and 2*gap for safety
            user_commit_buf = max(0.0, float(self.commit_buffer_minutes) * 60.0)
            self._commit_buffer_seconds = max(user_commit_buf, 2.0 * gap, 0.5 * overhead, 300.0)

            # Switch-back buffer: require significantly larger slack to leave OD back to SPOT
            user_switch_back_buf = max(0.0, float(self.switch_back_buffer_hours) * 3600.0)
            self._switch_back_buffer_seconds = max(user_switch_back_buf, 4.0 * gap, overhead)

            self._initialized = True

    def _get_done_seconds(self) -> float:
        l = self.task_done_time
        try:
            if l is self._done_cache_list:
                cur_len = len(l)
                if cur_len > self._done_cache_len:
                    # Incremental sum for appended segments
                    for i in range(self._done_cache_len, cur_len):
                        self._done_cache_sum += l[i]
                    self._done_cache_len = cur_len
                elif cur_len < self._done_cache_len:
                    # Fallback to full recompute if list shrank (unexpected)
                    self._done_cache_sum = sum(l)
                    self._done_cache_len = cur_len
                # else: unchanged
            else:
                # Different list object reference; recompute
                self._done_cache_sum = sum(l) if l else 0.0
                self._done_cache_len = len(l) if l else 0
                self._done_cache_list = l
            return float(self._done_cache_sum)
        except Exception:
            # Robust fallback
            try:
                return float(sum(l))
            except Exception:
                return float(getattr(self, "done_seconds", 0.0))

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._init_if_needed()

        # Fetch environment variables
        elapsed = float(self.env.elapsed_seconds)
        gap = float(self.env.gap_seconds)
        deadline = float(self.deadline)
        overhead = float(self.restart_overhead)

        # Compute remaining work and slack
        done = self._get_done_seconds()
        remaining = max(0.0, float(self.task_duration) - done)
        time_left = max(0.0, deadline - elapsed)
        slack = time_left - remaining

        # If task done, do nothing
        if remaining <= 0.0:
            return ClusterType.NONE

        # If already past deadline, best effort: run OD
        if time_left <= 0.0:
            self._od_locked = True
            return ClusterType.ON_DEMAND

        # Determine if currently on OD
        on_od = (last_cluster_type == ClusterType.ON_DEMAND)

        # Determine whether we must commit to OD now to guarantee on-time finish.
        # If not currently on OD, need to reserve overhead + safety buffer before deadline.
        commit_threshold = remaining + overhead + self._commit_buffer_seconds
        must_commit_od_now = (not on_od) and (time_left <= commit_threshold)

        if must_commit_od_now:
            self._od_locked = True
            return ClusterType.ON_DEMAND

        # If we are already committed (previously triggered), keep OD
        if on_od and self._od_locked:
            return ClusterType.ON_DEMAND

        # Consider switching back from OD to SPOT if safe and spot available
        if on_od and not self._od_locked:
            # Require substantial extra slack to move back to SPOT
            if has_spot and (slack >= (overhead + self._switch_back_buffer_seconds)):
                return ClusterType.SPOT
            # Otherwise stay on OD
            return ClusterType.ON_DEMAND

        # Not on OD and not required to commit yet: prefer SPOT if available, else wait
        if has_spot:
            return ClusterType.SPOT

        # Spot not available; if safe to wait, pause; else commit to OD
        if slack > (overhead + self._commit_buffer_seconds):
            return ClusterType.NONE
        else:
            self._od_locked = True
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        if isinstance(parser, argparse.ArgumentParser):
            parser.add_argument("--commit_buffer_minutes", type=float, default=10.0)
            parser.add_argument("--switch_back_buffer_hours", type=float, default=2.0)
        args, _ = parser.parse_known_args()
        return cls(args)