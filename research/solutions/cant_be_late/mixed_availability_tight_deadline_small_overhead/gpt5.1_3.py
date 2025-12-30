import numbers
from typing import Any, ClassVar

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME: ClassVar[str] = "my_solution"

    def __init__(self, args: Any = None):
        super().__init__(args)
        # Policy / progress tracking state
        self._policy_initialized: bool = False

        # Progress representation
        self._task_rep: str | None = None  # 'scalar', 'segments', 'fallback'
        self._progress: float = 0.0  # Estimated job progress in seconds

        # For 'segments' representation incremental update
        self._prev_task_len: int = 0
        self._prev_last_seg_length: float = 0.0

        # For fallback progress when task_done_time is unusable
        self._fallback_progress: float = 0.0
        self._fallback_prev_elapsed: float | None = None

        # Scheduling thresholds (initialized when env is available)
        self.total_slack: float = 0.0
        self.pure_spot_slack: float = 0.0
        self.commit_margin: float = 0.0

        # Phase control
        self.lock_in_ondemand: bool = False

    def solve(self, spec_path: str) -> "Solution":
        # Optional: could parse spec_path; unused here
        return self

    # ---------- Internal helpers ----------

    def _init_policy(self) -> None:
        # Called on first _step, when env and task attributes are available
        self.total_slack = max(0.0, float(self.deadline) - float(self.task_duration))

        # Use up to 50% of slack in pure-spot phase
        self.pure_spot_slack = 0.5 * self.total_slack

        # Leave some margin before hard deadline when switching permanently to OD
        if self.total_slack > 0.0:
            # Commit margin: min(0.5h, 50% of total slack)
            half_hour = 0.5 * 3600.0
            self.commit_margin = min(half_hour, 0.5 * self.total_slack)
        else:
            self.commit_margin = 0.0

        # Initialize fallback elapsed tracker
        self._fallback_prev_elapsed = float(self.env.elapsed_seconds)

        self.lock_in_ondemand = False
        self._policy_initialized = True

    @staticmethod
    def _seg_len(seg: Any) -> float | None:
        try:
            if isinstance(seg, (list, tuple)):
                if len(seg) >= 2:
                    start = float(seg[0])
                    end = float(seg[1])
                    return end - start
            else:
                start = getattr(seg, "start", None)
                end = getattr(seg, "end", None)
                if start is not None and end is not None:
                    return float(end) - float(start)
        except Exception:
            return None
        return None

    def _update_fallback_progress(self, last_cluster_type: ClusterType) -> None:
        if self._fallback_prev_elapsed is None:
            self._fallback_prev_elapsed = float(self.env.elapsed_seconds)
            return

        current_elapsed = float(self.env.elapsed_seconds)
        dt = current_elapsed - self._fallback_prev_elapsed
        if dt < 0.0:
            dt = 0.0

        if last_cluster_type is not None and last_cluster_type != ClusterType.NONE:
            self._fallback_progress += dt

        self._fallback_prev_elapsed = current_elapsed

    def _update_progress(self, last_cluster_type: ClusterType) -> None:
        # Try to use env.task_done_time; fall back to runtime estimation if needed.
        task_done = getattr(self, "task_done_time", None)

        # Always advance fallback estimate in case we need it
        self._update_fallback_progress(last_cluster_type)

        if task_done is None:
            # No info; rely on fallback
            self._task_rep = "fallback"
            self._progress = self._fallback_progress
            return

        # Empty list: no work done yet
        if not task_done:
            if self._task_rep is None:
                # Representation not yet known; keep zero or fallback
                self._progress = max(self._progress, self._fallback_progress)
            elif self._task_rep == "fallback":
                self._progress = self._fallback_progress
            return

        # Infer representation once
        if self._task_rep is None:
            first = task_done[0]
            if isinstance(first, numbers.Number):
                self._task_rep = "scalar"
            else:
                seg_len = self._seg_len(first)
                if seg_len is not None:
                    self._task_rep = "segments"
                    total = 0.0
                    for seg in task_done:
                        l = self._seg_len(seg)
                        if l is not None and l > 0.0:
                            total += l
                    self._progress = total
                    self._prev_task_len = len(task_done)
                    last_len = self._seg_len(task_done[-1])
                    self._prev_last_seg_length = last_len if last_len is not None else 0.0
                    return
                else:
                    self._task_rep = "fallback"

        # Update according to representation
        if self._task_rep == "scalar":
            try:
                self._progress = float(task_done[-1])
            except Exception:
                # Fall back if unexpected structure
                self._task_rep = "fallback"
                self._progress = self._fallback_progress
        elif self._task_rep == "segments":
            segs = task_done
            n = len(segs)
            if n == 0:
                return

            last_seg = segs[-1]
            last_len = self._seg_len(last_seg)
            if last_len is None:
                last_len = 0.0

            if n > self._prev_task_len:
                # New segments appended
                for i in range(self._prev_task_len, n - 1):
                    l = self._seg_len(segs[i])
                    if l is not None and l > 0.0:
                        self._progress += l
                inc = max(0.0, last_len)
            else:
                # Same count; last segment extended
                inc = max(0.0, last_len - self._prev_last_seg_length)

            self._progress += inc
            self._prev_task_len = n
            self._prev_last_seg_length = last_len
        else:
            # Fallback representation
            self._progress = self._fallback_progress

    # ---------- Core decision logic ----------

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not self._policy_initialized:
            self._init_policy()

        # Update progress estimate
        self._update_progress(last_cluster_type)

        elapsed = float(self.env.elapsed_seconds)
        progress = max(0.0, min(float(self.task_duration), float(self._progress)))
        remaining = max(0.0, float(self.task_duration) - progress)
        time_to_deadline = float(self.deadline) - elapsed

        # Spent slack = elapsed wall-clock minus progress on job
        spent_slack = max(0.0, elapsed - progress)

        # If job already effectively done, no need to run more
        if remaining <= 0.0:
            return ClusterType.NONE

        # If time is already past deadline, nothing to do; choose NONE to avoid extra cost
        if time_to_deadline <= 0.0:
            return ClusterType.NONE

        # If we've already decided to lock into on-demand, always use it
        if self.lock_in_ondemand:
            return ClusterType.ON_DEMAND

        # If there is no slack at all, must run on-demand continuously
        if self.total_slack <= 0.0:
            self.lock_in_ondemand = True
            return ClusterType.ON_DEMAND

        # Safety: if even running flat-out from now (no idle) barely makes the deadline, lock into OD
        # We require a small positive margin (commit_margin) to account for step granularity/overheads.
        if time_to_deadline <= remaining + self.commit_margin:
            self.lock_in_ondemand = True
            return ClusterType.ON_DEMAND

        # Commit to on-demand when consumed slack approaches total slack minus margin
        if spent_slack >= self.total_slack - self.commit_margin:
            self.lock_in_ondemand = True
            return ClusterType.ON_DEMAND

        # Phase selection based on spent slack
        if spent_slack < self.pure_spot_slack:
            # Phase 1: pure spot usage, idle when no spot
            if has_spot:
                return ClusterType.SPOT
            else:
                return ClusterType.NONE
        else:
            # Phase 2: hybrid - run continuously; use spot when available, OD otherwise
            if has_spot:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser) -> "Solution":
        args, _ = parser.parse_known_args()
        return cls(args)