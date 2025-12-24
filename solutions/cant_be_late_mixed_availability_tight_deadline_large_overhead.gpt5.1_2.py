import math
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        # Initialize policy-related attributes; env will be set later.
        self.force_on_demand = False
        self._policy_initialized = False
        return self

    def _init_policy_if_needed(self):
        if getattr(self, "_policy_initialized", False):
            return
        self._policy_initialized = True

        # Default values in case attributes are missing
        gap = getattr(self.env, "gap_seconds", 1.0)
        restart = getattr(self, "restart_overhead", 0.0)

        deadline = getattr(self, "deadline", None)
        task_duration = getattr(self, "task_duration", None)

        if isinstance(deadline, (int, float)) and isinstance(task_duration, (int, float)):
            initial_slack = max(0.0, float(deadline) - float(task_duration))
        else:
            initial_slack = 0.0

        self._initial_slack = initial_slack

        if initial_slack <= 0.0:
            # No slack: always run on-demand.
            commit = restart + 3.0 * gap
            wait = commit
        else:
            # Commit threshold: when slack drops this low, switch permanently to OD.
            commit = max(0.2 * initial_slack, 2.0 * restart + 4.0 * gap)
            commit = min(commit, 0.8 * initial_slack)

            # Wait threshold: above this slack, it's OK to pause when no spot.
            wait = max(0.5 * initial_slack, commit + restart + 2.0 * gap)
            wait = min(wait, 0.9 * initial_slack)

            if wait < commit:
                wait = commit

        self._commit_threshold = commit
        self._wait_threshold = wait

        if not hasattr(self, "force_on_demand"):
            self.force_on_demand = False

    def _estimate_progress(self) -> float:
        segs = getattr(self, "task_done_time", None)
        if not segs:
            return 0.0

        total = 0.0
        for seg in segs:
            if seg is None:
                continue

            # Numeric segment: treat as duration.
            if isinstance(seg, (int, float)) and not isinstance(seg, bool):
                total += float(seg)
                continue

            # Dict-like segment.
            if isinstance(seg, dict):
                dur = seg.get("duration", None)
                if dur is not None:
                    total += float(dur)
                    continue
                start = seg.get("start", seg.get("begin", seg.get("s", None)))
                end = seg.get("end", seg.get("finish", seg.get("e", None)))
                if start is not None and end is not None:
                    try:
                        total += max(0.0, float(end) - float(start))
                    except (TypeError, ValueError):
                        pass
                continue

            # Sequence segment (list/tuple).
            if isinstance(seg, (list, tuple)):
                if len(seg) >= 2 and isinstance(seg[0], (int, float)) and isinstance(seg[1], (int, float)):
                    total += max(0.0, float(seg[1]) - float(seg[0]))
                elif len(seg) == 1 and isinstance(seg[0], (int, float)):
                    total += float(seg[0])
                continue

            # Generic object with attributes.
            dur = getattr(seg, "duration", None)
            if dur is not None:
                try:
                    total += float(dur)
                    continue
                except (TypeError, ValueError):
                    pass
            start = getattr(seg, "start", getattr(seg, "begin", None))
            end = getattr(seg, "end", getattr(seg, "finish", None))
            if start is not None and end is not None:
                try:
                    total += max(0.0, float(end) - float(start))
                except (TypeError, ValueError):
                    pass

        td = getattr(self, "task_duration", None)
        if isinstance(td, (int, float)):
            td_f = float(td)
            if total > td_f:
                total = td_f
        return total

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._init_policy_if_needed()

        # Estimate remaining work.
        task_duration = float(self.task_duration)
        done = self._estimate_progress()
        remaining_compute = max(0.0, task_duration - done)

        if remaining_compute <= 0.0:
            # Job finished.
            self.force_on_demand = False
            return ClusterType.NONE

        # Time left until deadline.
        now = getattr(self.env, "elapsed_seconds", 0.0)
        deadline_attr = getattr(self, "deadline", None)
        if isinstance(deadline_attr, (int, float)):
            deadline = float(deadline_attr)
        else:
            deadline = float("inf")
        remaining_wall = max(0.0, deadline - now)

        slack = remaining_wall - remaining_compute

        # If we're out of slack or very tight, force on-demand.
        if slack <= 0.0 or slack <= self._commit_threshold:
            self.force_on_demand = True

        if self.force_on_demand:
            return ClusterType.ON_DEMAND

        # Not yet committed to on-demand.
        if has_spot:
            # Favor spot whenever available while we still have sufficient slack.
            return ClusterType.SPOT

        # No spot available: decide between waiting and on-demand.
        if slack > self._wait_threshold:
            # Plenty of slack beyond target buffer: can afford to wait.
            return ClusterType.NONE
        else:
            # Need to keep making progress: use on-demand.
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
