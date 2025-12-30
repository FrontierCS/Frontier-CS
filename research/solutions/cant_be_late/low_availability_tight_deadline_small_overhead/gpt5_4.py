from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_lst_v1"

    def __init__(self, args=None):
        try:
            super().__init__(args)
        except Exception:
            try:
                super().__init__()
            except Exception:
                pass
        self._committed_to_od = False
        self._done_sum_cache = 0.0
        self._last_done_len = 0
        self._episode_initialized = False

        # Optional args
        self.margin_extra_seconds = None
        if args is not None:
            extr = getattr(args, "margin_extra_minutes", None)
            if extr is not None:
                try:
                    self.margin_extra_seconds = float(extr) * 60.0
                except Exception:
                    self.margin_extra_seconds = None
        self._default_extra_margin_seconds = 300.0  # 5 minutes

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _init_episode_if_needed(self):
        # Reinitialize state at the beginning of each episode
        if getattr(self.env, "elapsed_seconds", 0.0) == 0.0 or not self._episode_initialized:
            self._committed_to_od = False
            # Initialize cached progress
            if hasattr(self, "task_done_time"):
                self._last_done_len = len(self.task_done_time)
                if self._last_done_len > 0:
                    try:
                        self._done_sum_cache = sum(self.task_done_time)
                    except Exception:
                        # Fallback: recompute incrementally if sum fails
                        self._done_sum_cache = 0.0
                        for v in self.task_done_time:
                            self._done_sum_cache += v
                else:
                    self._done_sum_cache = 0.0
            else:
                self._last_done_len = 0
                self._done_sum_cache = 0.0
            self._episode_initialized = True

    def _update_done_sum(self):
        # Efficiently update cached sum if new segments appended
        try:
            current_len = len(self.task_done_time)
        except Exception:
            # Fallback: compute from attribute directly
            return self._done_sum_cache
        if current_len < self._last_done_len:
            # List replaced or reset; recompute full sum
            try:
                self._done_sum_cache = sum(self.task_done_time)
            except Exception:
                s = 0.0
                for v in self.task_done_time:
                    s += v
                self._done_sum_cache = s
            self._last_done_len = current_len
        elif current_len > self._last_done_len:
            # Incremental addition
            s_add = 0.0
            for i in range(self._last_done_len, current_len):
                s_add += self.task_done_time[i]
            self._done_sum_cache += s_add
            self._last_done_len = current_len
        return self._done_sum_cache

    def _calc_margin(self):
        gap = getattr(self.env, "gap_seconds", 60.0) or 0.0
        ro = getattr(self, "restart_overhead", 0.0) or 0.0
        extra = self.margin_extra_seconds if self.margin_extra_seconds is not None else self._default_extra_margin_seconds
        # Margin accounts for:
        # - one restart overhead to switch to OD
        # - 2 timesteps of discretization latency
        # - an extra buffer
        margin = ro + 2.0 * gap + extra
        return margin

    def _must_commit_to_od_now(self, last_cluster_type, remaining, time_left):
        overhead_now = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else (getattr(self, "restart_overhead", 0.0) or 0.0)
        margin = self._calc_margin()
        need = remaining + overhead_now + margin
        return need >= time_left

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._init_episode_if_needed()

        # If we've already committed to OD, never go back to spot
        if self._committed_to_od:
            return ClusterType.ON_DEMAND

        # Compute remaining work and time to deadline
        done = self._update_done_sum()
        remaining = max(0.0, (getattr(self, "task_duration", 0.0) or 0.0) - done)
        time_left = (getattr(self, "deadline", 0.0) or 0.0) - (getattr(self.env, "elapsed_seconds", 0.0) or 0.0)

        # If no time left, choose OD to minimize additional risk
        if time_left <= 0.0:
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        # If nothing remains, do nothing
        if remaining <= 0.0:
            return ClusterType.NONE

        # Decide whether we must commit to OD now to guarantee completion
        if self._must_commit_to_od_now(last_cluster_type, remaining, time_left):
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        # Otherwise, prefer spot when available, else wait (NONE) to save cost
        if has_spot:
            return ClusterType.SPOT
        else:
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        try:
            parser.add_argument("--margin_extra_minutes", type=float, default=None)
        except Exception:
            pass
        args, _ = parser.parse_known_args()
        return cls(args)