from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_heuristic"

    def __init__(self, args=None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except TypeError:
                pass
        self.args = args
        self._force_od = False
        self._guard_time = None
        self._work_done_accum = 0.0
        self._last_task_segments_count = 0
        self._last_task_done_time_ref = None
        self._last_elapsed_seconds_seen = None

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _reset_episode_state(self):
        self._force_od = False
        self._guard_time = None
        self._work_done_accum = 0.0
        self._last_task_segments_count = 0
        self._last_task_done_time_ref = None

    def _update_work_done(self):
        tlist = getattr(self, "task_done_time", None)

        if tlist is None:
            self._work_done_accum = 0.0
            self._last_task_segments_count = 0
            self._last_task_done_time_ref = None
            return

        if not isinstance(tlist, (list, tuple)):
            try:
                self._work_done_accum = float(tlist)
            except (TypeError, ValueError):
                pass
            self._last_task_segments_count = 1
            self._last_task_done_time_ref = tlist
            return

        if tlist is not self._last_task_done_time_ref:
            total = 0.0
            for v in tlist:
                try:
                    total += float(v)
                except (TypeError, ValueError):
                    continue
            self._work_done_accum = total
            self._last_task_segments_count = len(tlist)
            self._last_task_done_time_ref = tlist
        else:
            n = len(tlist)
            if n > self._last_task_segments_count:
                for v in tlist[self._last_task_segments_count:]:
                    try:
                        self._work_done_accum += float(v)
                    except (TypeError, ValueError):
                        continue
                self._last_task_segments_count = n

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        elapsed = getattr(self.env, "elapsed_seconds", 0.0)

        if self._last_elapsed_seconds_seen is None or elapsed < self._last_elapsed_seconds_seen:
            self._reset_episode_state()
        self._last_elapsed_seconds_seen = elapsed

        if self._guard_time is None:
            gap = getattr(self.env, "gap_seconds", 0.0) or 0.0
            restart = getattr(self, "restart_overhead", getattr(self.env, "restart_overhead", 0.0)) or 0.0
            self._guard_time = gap + restart

        self._update_work_done()

        task_duration = getattr(self, "task_duration", getattr(self.env, "task_duration", 0.0))
        try:
            total_dur = float(task_duration)
        except (TypeError, ValueError):
            total_dur = 0.0

        remaining_work = total_dur - self._work_done_accum
        if remaining_work <= 0.0:
            self._force_od = False
            return ClusterType.NONE

        if self._force_od:
            return ClusterType.ON_DEMAND

        deadline_attr = getattr(self, "deadline", getattr(self.env, "deadline", None))
        if deadline_attr is not None:
            try:
                deadline_val = float(deadline_attr)
            except (TypeError, ValueError):
                deadline_val = None
        else:
            deadline_val = None

        if deadline_val is not None:
            restart_overhead = getattr(self, "restart_overhead", getattr(self.env, "restart_overhead", 0.0)) or 0.0
            worst_finish_time = elapsed + restart_overhead + remaining_work
            threshold = deadline_val - self._guard_time
            if worst_finish_time >= threshold:
                self._force_od = True
                return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)