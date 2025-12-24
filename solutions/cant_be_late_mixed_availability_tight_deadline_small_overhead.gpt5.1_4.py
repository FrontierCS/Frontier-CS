import math
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args):
        super().__init__(args)
        self._progress_cache = 0.0
        self._last_task_done_index = 0
        self._policy_initialized = False
        self._use_on_demand_only = False
        self._total_slack = 0.0
        self._fallback_slack = 0.0
        self._idle_slack = 0.0

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _init_policy(self):
        if self._policy_initialized:
            return

        try:
            task_dur = float(self.task_duration)
        except Exception:
            task_dur = 0.0

        try:
            deadline = float(self.deadline)
        except Exception:
            deadline = task_dur

        total_slack = max(0.0, deadline - task_dur)
        self._total_slack = total_slack

        env = getattr(self, "env", None)
        gap_seconds = float(getattr(env, "gap_seconds", 0.0)) if env is not None else 0.0
        restart_overhead = float(getattr(self, "restart_overhead", 0.0))

        # Fallback slack: once slack <= this, we switch permanently to on-demand.
        # Ensure we leave room for at least one restart and a few steps of discretization.
        min_fallback = restart_overhead * 5.0 + gap_seconds * 2.0
        fallback_slack = max(min_fallback, total_slack * 0.15)

        # Idle slack: while slack >= this, if no spot we may choose to idle (NONE).
        idle_slack = max(fallback_slack * 1.5, total_slack * 0.4)

        # Clamp to available slack.
        if idle_slack > total_slack:
            idle_slack = total_slack
        if fallback_slack > idle_slack:
            fallback_slack = idle_slack * 0.7 if idle_slack > 0 else 0.0

        self._fallback_slack = fallback_slack
        self._idle_slack = idle_slack
        self._policy_initialized = True

    def _update_progress_cache(self) -> float:
        """Incrementally update cached task progress from task_done_time."""
        task_done = getattr(self, "task_done_time", None)
        if task_done is None:
            return self._progress_cache

        try:
            length = len(task_done)
        except TypeError:
            # Not iterable; best effort
            try:
                self._progress_cache = float(task_done)
            except Exception:
                pass
            return self._progress_cache

        if length <= self._last_task_done_index:
            return self._progress_cache

        new_segments = task_done[self._last_task_done_index:length]
        add = 0.0
        for seg in new_segments:
            if isinstance(seg, (int, float)):
                add += float(seg)
            elif isinstance(seg, (list, tuple)) and len(seg) >= 2:
                try:
                    add += float(seg[1]) - float(seg[0])
                except Exception:
                    continue
            else:
                start = getattr(seg, "start", None)
                end = getattr(seg, "end", None)
                if start is not None and end is not None:
                    try:
                        add += float(end) - float(start)
                    except Exception:
                        continue
                else:
                    try:
                        add += float(seg)
                    except Exception:
                        continue

        self._progress_cache += add
        self._last_task_done_index = length

        try:
            task_dur = float(self.task_duration)
            if self._progress_cache > task_dur:
                self._progress_cache = task_dur
        except Exception:
            pass

        return self._progress_cache

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not self._policy_initialized:
            self._init_policy()

        progress = self._update_progress_cache()

        try:
            task_dur = float(self.task_duration)
        except Exception:
            task_dur = 0.0

        # If somehow already done, no need to run anything.
        if progress >= task_dur:
            return ClusterType.NONE

        if self._use_on_demand_only:
            return ClusterType.ON_DEMAND

        env = self.env
        try:
            elapsed = float(env.elapsed_seconds)
        except Exception:
            elapsed = 0.0

        try:
            deadline = float(self.deadline)
        except Exception:
            deadline = elapsed + (task_dur - progress)

        remaining_wall = max(0.0, deadline - elapsed)
        remaining_work = max(0.0, task_dur - progress)
        slack = max(0.0, remaining_wall - remaining_work)

        # If we've used up nearly all slack, permanently fall back to on-demand.
        if slack <= self._fallback_slack:
            self._use_on_demand_only = True
            return ClusterType.ON_DEMAND

        # While we're not in the fallback region, prefer spot when available.
        if has_spot:
            return ClusterType.SPOT

        # No spot: decide between idling and using on-demand.
        if slack >= self._idle_slack:
            # Plenty of slack left; wait for cheaper spot capacity.
            return ClusterType.NONE
        else:
            # Slack shrinking; use on-demand to keep on track.
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
