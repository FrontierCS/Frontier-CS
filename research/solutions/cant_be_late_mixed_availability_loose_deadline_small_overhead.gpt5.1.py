from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_thresholds_v1"

    def solve(self, spec_path: str) -> "Solution":
        # Optional: could load configuration from spec_path.
        return self

    def _update_progress_cache(self):
        """Incrementally track total completed task duration."""
        if not hasattr(self, "_total_task_done"):
            self._total_task_done = 0.0
            self._last_task_done_len = 0
            self._segments_are_pairs = None

        task_segments = getattr(self, "task_done_time", None)
        if not task_segments:
            return

        try:
            length = len(task_segments)
        except TypeError:
            # Not a sized collection; fall back to best-effort full sum once.
            if self._last_task_done_len == 0:
                total = 0.0
                for seg in task_segments:
                    try:
                        if isinstance(seg, (list, tuple)) and len(seg) == 2:
                            start, end = seg
                            dt = float(end) - float(start)
                        else:
                            dt = float(seg)
                    except Exception:
                        continue
                    if dt > 0:
                        total += dt
                self._total_task_done = total
                self._last_task_done_len = 1  # mark as processed
            return

        if length <= self._last_task_done_len:
            return

        # Infer segment representation once we see at least one element.
        if self._segments_are_pairs is None and length > 0:
            first = task_segments[0]
            self._segments_are_pairs = isinstance(first, (list, tuple)) and len(first) == 2

        new_segments = task_segments[self._last_task_done_len : length]

        total_add = 0.0
        if self._segments_are_pairs:
            for seg in new_segments:
                try:
                    start, end = seg
                    dt = float(end) - float(start)
                except Exception:
                    # Fallback: try treating as scalar duration.
                    try:
                        dt = float(seg)
                    except Exception:
                        continue
                if dt > 0:
                    total_add += dt
        else:
            for seg in new_segments:
                try:
                    dt = float(seg)
                except Exception:
                    # Fallback: try (start, end) pair.
                    try:
                        start, end = seg
                        dt = float(end) - float(start)
                    except Exception:
                        continue
                if dt > 0:
                    total_add += dt

        self._total_task_done += total_add
        self._last_task_done_len = length

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update cached progress.
        self._update_progress_cache()
        done = getattr(self, "_total_task_done", 0.0)

        total_duration = float(self.task_duration)
        remaining = max(0.0, total_duration - done)

        # If task is completed, do nothing.
        if remaining <= 0.0:
            return ClusterType.NONE

        env = self.env
        elapsed = float(env.elapsed_seconds)
        deadline = float(self.deadline)

        time_left = deadline - elapsed

        # If already at or past deadline, just use on-demand to finish ASAP.
        if time_left <= 0.0:
            return ClusterType.ON_DEMAND

        slack = time_left - remaining

        # If we mathematically cannot finish even with full on-demand, still use OD.
        if slack <= 0.0:
            return ClusterType.ON_DEMAND

        gap = float(getattr(env, "gap_seconds", 0.0) or 0.0)
        restart_overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        max_waste_step = gap + restart_overhead

        # Safety-aware slack thresholds (in seconds).
        # S2: commit-to-on-demand threshold (low slack).
        # S1: stop-idling threshold (medium slack).
        s2 = max(0.05 * total_duration, 8.0 * max_waste_step)
        s1 = max(0.25 * total_duration, 2.0 * s2)

        # Phase 3: Low slack -> always on-demand.
        if slack <= s2:
            return ClusterType.ON_DEMAND

        # Phase 2: Medium slack -> prefer spot but fall back to on-demand when spot unavailable.
        if slack <= s1:
            if has_spot:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND

        # Phase 1: High slack -> use spot when available, otherwise pause (no cost).
        if has_spot:
            return ClusterType.SPOT
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)