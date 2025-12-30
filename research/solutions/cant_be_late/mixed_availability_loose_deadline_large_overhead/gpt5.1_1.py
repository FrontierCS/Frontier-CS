from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_v1"

    def __init__(self, args=None):
        super().__init__(args)
        # Internal tracking for efficient progress computation
        self._progress_init_done = False
        self._last_elapsed = 0.0
        self._last_task_len = 0
        self._task_sum_assuming_durations = 0.0
        self._task_max_value = 0.0

    def solve(self, spec_path: str) -> "Solution":
        # No spec-based configuration for now
        return self

    def _reset_progress_tracking(self):
        task_list = getattr(self, "task_done_time", []) or []
        self._last_task_len = len(task_list)
        if self._last_task_len > 0:
            # Initialize cached sum and max
            total = 0.0
            max_v = float(task_list[0])
            for v in task_list:
                fv = float(v)
                total += fv
                if fv > max_v:
                    max_v = fv
            self._task_sum_assuming_durations = total
            self._task_max_value = max_v
        else:
            self._task_sum_assuming_durations = 0.0
            self._task_max_value = 0.0
        self._last_elapsed = getattr(self.env, "elapsed_seconds", 0.0)
        self._progress_init_done = True

    def _update_progress_tracking(self):
        # Initialize or reset if new episode detected
        current_elapsed = getattr(self.env, "elapsed_seconds", 0.0)
        if (not self._progress_init_done) or current_elapsed < self._last_elapsed - 1e-6:
            self._reset_progress_tracking()
            return

        task_list = getattr(self, "task_done_time", []) or []
        cur_len = len(task_list)

        if cur_len < self._last_task_len:
            # Environment reset or unexpected shrink; reinitialize safely
            self._reset_progress_tracking()
            return

        # Process any new entries incrementally
        if cur_len > self._last_task_len:
            for i in range(self._last_task_len, cur_len):
                v = float(task_list[i])
                self._task_sum_assuming_durations += v
                if v > self._task_max_value:
                    self._task_max_value = v
            self._last_task_len = cur_len

        self._last_elapsed = current_elapsed

    def _get_progress_seconds(self) -> float:
        """
        Estimate total completed work seconds from task_done_time.

        Handles both possible representations:
        - List of segment durations
        - List of cumulative completion times
        """
        self._update_progress_tracking()

        elapsed = getattr(self.env, "elapsed_seconds", 0.0)
        total_duration_like = self._task_sum_assuming_durations
        max_value = self._task_max_value

        if self._last_task_len == 0:
            progress = 0.0
        else:
            # If the sum of entries is significantly larger than elapsed time,
            # interpret entries as cumulative completion times. Otherwise,
            # treat them as segment durations.
            if elapsed > 0.0 and total_duration_like > elapsed * 1.05:
                # Likely cumulative completion times -> progress is max value
                progress = max_value
            else:
                # Likely segment durations
                progress = total_duration_like

        task_duration = float(getattr(self, "task_duration", 0.0))
        if task_duration > 0.0:
            # Clamp to [0, task_duration]
            if progress < 0.0:
                progress = 0.0
            elif progress > task_duration:
                progress = task_duration
        else:
            if progress < 0.0:
                progress = 0.0

        return progress

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Fallback simple policy if environment attributes are missing
        if not hasattr(self, "env") or not hasattr(self.env, "elapsed_seconds"):
            return ClusterType.SPOT if has_spot else ClusterType.ON_DEMAND

        if not hasattr(self, "task_duration") or not hasattr(self, "deadline"):
            return ClusterType.SPOT if has_spot else ClusterType.ON_DEMAND

        task_duration = float(self.task_duration)
        deadline = float(self.deadline)
        elapsed = float(self.env.elapsed_seconds)
        gap = float(getattr(self.env, "gap_seconds", 0.0))
        restart_overhead = float(getattr(self, "restart_overhead", 0.0))

        progress = self._get_progress_seconds()
        remaining = task_duration - progress
        if remaining <= 0.0:
            # Task already completed; no need to run anything
            return ClusterType.NONE

        time_left = deadline - elapsed
        if time_left <= 0.0:
            # Already past deadline; run on-demand to minimize further delay
            return ClusterType.ON_DEMAND

        # Guard buffer accounts for:
        # - One more decision interval (gap)
        # - A worst-case restart overhead before stable on-demand
        guard_buffer = gap + restart_overhead

        # Safe to risk one more step on spot/idle only if we still have
        # enough time after a possible gap + overhead to finish remaining work
        if time_left >= remaining + guard_buffer:
            if has_spot:
                return ClusterType.SPOT
            else:
                # Wait (no cost) for spot if we still have enough slack
                return ClusterType.NONE
        else:
            # Not enough slack left to risk further preemptions or idling;
            # switch to on-demand to guarantee completion.
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)