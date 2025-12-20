from typing import Any, Iterable
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args=None):
        super().__init__(args)
        # Episode-specific state
        self.initial_slack: float | None = None
        self.wait_slack_threshold: float | None = None
        self.stop_spot_threshold: float | None = None
        self._last_elapsed: float | None = None

        # Cached task progress
        self._cached_done_time: float = 0.0
        self._last_task_done_len: int | None = None

    def solve(self, spec_path: str) -> "Solution":
        # Optional configuration via spec_path can be added here.
        return self

    # ---- Internal helpers ----

    def _reset_episode_state(self) -> None:
        """Reset state at the beginning of each episode."""
        if not hasattr(self, "env") or self.env is None:
            return

        # Initial slack: time buffer (seconds) = deadline - required work
        self.initial_slack = max(float(self.deadline) - float(self.task_duration), 0.0)

        if self.initial_slack <= 0.0:
            # No slack: must rely on on-demand all the time
            self.wait_slack_threshold = 0.0
            self.stop_spot_threshold = 0.0
        else:
            s = self.initial_slack
            # Keep 40% of slack as safety buffer, spend up to 60% on waiting
            self.wait_slack_threshold = 0.4 * s
            # Stop using spot entirely when slack becomes very small
            self.stop_spot_threshold = max(0.05 * s, 5.0 * float(self.restart_overhead))
            # Ensure ordering: stop_spot < wait_slack
            if self.stop_spot_threshold >= self.wait_slack_threshold:
                self.stop_spot_threshold = 0.5 * self.wait_slack_threshold

        self._cached_done_time = 0.0
        self._last_task_done_len = 0
        self._last_elapsed = float(self.env.elapsed_seconds)

    def _slow_sum_done_time(self, segments: Iterable[Any]) -> float:
        """Robustly sum completed work from arbitrary segment representations."""
        total = 0.0
        for seg in segments:
            if seg is None:
                continue
            if isinstance(seg, (int, float)):
                total += float(seg)
            elif isinstance(seg, (list, tuple)):
                if not seg:
                    continue
                if len(seg) == 1:
                    val = seg[0]
                    try:
                        total += float(val)
                    except Exception:
                        continue
                else:
                    a, b = seg[0], seg[1]
                    try:
                        af = float(a)
                        bf = float(b)
                        total += abs(bf - af)
                    except Exception:
                        # Fallback: try to sum elements that are numeric
                        for v in seg:
                            try:
                                total += float(v)
                            except Exception:
                                continue
            elif isinstance(seg, dict):
                if "duration" in seg:
                    try:
                        total += float(seg["duration"])
                    except Exception:
                        pass
                elif "start" in seg and "end" in seg:
                    try:
                        total += abs(float(seg["end"]) - float(seg["start"]))
                    except Exception:
                        pass
                else:
                    # Fallback: use any numeric value
                    for v in seg.values():
                        try:
                            total += float(v)
                            break
                        except Exception:
                            continue
            else:
                try:
                    total += float(seg)
                except Exception:
                    continue
        return total

    def _update_done_time_cache(self) -> float:
        """Incrementally update cached completed work."""
        # Prefer direct attribute; fall back to env if needed
        segments = getattr(self, "task_done_time", None)
        if segments is None and hasattr(self, "env") and hasattr(self.env, "task_done_time"):
            segments = self.env.task_done_time

        if segments is None:
            # As a last resort, try env.task_done if present
            if hasattr(self, "env") and hasattr(self.env, "task_done"):
                try:
                    self._cached_done_time = float(self.env.task_done)
                except Exception:
                    self._cached_done_time = 0.0
            return self._cached_done_time

        if isinstance(segments, (int, float)):
            self._cached_done_time = float(segments)
            self._last_task_done_len = None
            return self._cached_done_time

        # If segments is not sized, fall back to full summation each time
        try:
            n = len(segments)  # type: ignore[arg-type]
        except TypeError:
            self._cached_done_time = self._slow_sum_done_time(segments)  # type: ignore[arg-type]
            self._last_task_done_len = None
            return self._cached_done_time

        # Handle potential reset or list shrink
        if self._last_task_done_len is None or n < self._last_task_done_len:
            self._cached_done_time = self._slow_sum_done_time(segments)
            self._last_task_done_len = n
            return self._cached_done_time

        # No new segments
        if n == self._last_task_done_len:
            return self._cached_done_time

        # New segments appended
        try:
            new_segments = segments[self._last_task_done_len:n]  # type: ignore[index]
        except Exception:
            # If slicing fails, recompute from scratch
            self._cached_done_time = self._slow_sum_done_time(segments)
            self._last_task_done_len = n
            return self._cached_done_time

        increment = self._slow_sum_done_time(new_segments)
        self._cached_done_time += increment
        self._last_task_done_len = n
        return self._cached_done_time

    # ---- Core decision logic ----

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        current_elapsed = float(getattr(self.env, "elapsed_seconds", 0.0))

        # Detect new episode (elapsed time reset)
        if self._last_elapsed is None or current_elapsed < self._last_elapsed:
            self._reset_episode_state()
        else:
            self._last_elapsed = current_elapsed

        # Ensure thresholds are initialized (in case env changed after init)
        if self.initial_slack is None:
            self._reset_episode_state()

        # Compute remaining work
        task_duration = float(self.task_duration)
        done_time = self._update_done_time_cache()
        remaining_work = max(task_duration - done_time, 0.0)

        # If work is finished, do nothing to avoid cost
        if remaining_work <= 0.0:
            return ClusterType.NONE

        time_left = float(self.deadline) - current_elapsed

        # If already at/past deadline, just use on-demand to finish ASAP
        if time_left <= 0.0:
            return ClusterType.ON_DEMAND

        # Slack = free time buffer if we ran continuously from now
        slack = time_left - remaining_work

        # If slack is non-positive, we're behind; use on-demand
        if slack <= 0.0:
            return ClusterType.ON_DEMAND

        # Thresholds (in seconds)
        high_thr = float(self.wait_slack_threshold or 0.0)
        low_thr = float(self.stop_spot_threshold or 0.0)

        # Safety: ensure ordering and bounds
        if self.initial_slack is not None:
            if high_thr > self.initial_slack:
                high_thr = self.initial_slack
            if low_thr >= high_thr:
                low_thr = 0.5 * high_thr

        # Phase 3: Very little slack left -> avoid any further spot risk
        if slack <= low_thr + 1e-9:
            return ClusterType.ON_DEMAND

        # Phase 1: Plenty of slack -> wait for spot when unavailable
        if slack > high_thr + 1e-9:
            if has_spot:
                return ClusterType.SPOT
            else:
                return ClusterType.NONE

        # Phase 2: Moderate slack -> use spot when available, OD otherwise
        if has_spot:
            return ClusterType.SPOT
        else:
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
