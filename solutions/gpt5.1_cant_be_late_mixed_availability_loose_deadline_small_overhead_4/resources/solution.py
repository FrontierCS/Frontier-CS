from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        self._force_on_demand = False
        return self

    def _get_task_duration(self) -> float:
        val = getattr(self, "task_duration", None)
        try:
            td = float(val)
            if td > 0.0:
                return td
        except (TypeError, ValueError):
            pass
        deadline_val = getattr(self, "deadline", None)
        try:
            dl = float(deadline_val)
            if dl > 0.0:
                return dl
        except (TypeError, ValueError):
            pass
        return 0.0

    def _estimate_work_done(self) -> float:
        td = self._get_task_duration()
        segments = getattr(self, "task_done_time", None)
        if not segments:
            return 0.0
        done = 0.0
        for seg in segments:
            if seg is None:
                continue
            cand_list = []
            try:
                if isinstance(seg, (int, float)):
                    v = float(seg)
                    if v >= 0.0:
                        cand_list.append(v)
                elif isinstance(seg, (list, tuple)):
                    if len(seg) >= 1:
                        try:
                            v0 = float(seg[0])
                            if v0 >= 0.0:
                                cand_list.append(v0)
                        except (TypeError, ValueError):
                            v0 = None
                        else:
                            v0 = float(seg[0])
                    else:
                        v0 = None
                    v1 = None
                    if len(seg) >= 2:
                        try:
                            v1 = float(seg[1])
                            if v1 >= 0.0:
                                cand_list.append(v1)
                        except (TypeError, ValueError):
                            v1 = None
                    if v0 is not None and v1 is not None:
                        diff = v1 - v0
                        if diff >= 0.0:
                            cand_list.append(diff)
                else:
                    start_attr = getattr(seg, "start", None)
                    end_attr = getattr(seg, "end", None)
                    if end_attr is not None:
                        try:
                            ve = float(end_attr)
                            if ve >= 0.0:
                                cand_list.append(ve)
                        except (TypeError, ValueError):
                            pass
                    if start_attr is not None and end_attr is not None:
                        try:
                            vs = float(start_attr)
                            ve = float(end_attr)
                            diff = ve - vs
                            if diff >= 0.0:
                                cand_list.append(diff)
                        except (TypeError, ValueError):
                            pass
                    if not cand_list:
                        try:
                            v = float(seg)
                            if v >= 0.0:
                                cand_list.append(v)
                        except (TypeError, ValueError):
                            pass
            except Exception:
                cand_list = []

            if not cand_list:
                continue

            v = min(cand_list)
            if td > 0.0 and v > td:
                v = td
            if v > done:
                done = v

        if td > 0.0 and done > td:
            done = td
        if done < 0.0:
            done = 0.0
        return done

    def _estimate_remaining_work(self) -> float:
        td = self._get_task_duration()
        if td <= 0.0:
            # Unknown duration: be conservative and assume full remaining equals deadline.
            deadline_val = getattr(self, "deadline", None)
            try:
                dl = float(deadline_val)
                if dl > 0.0:
                    return dl
            except (TypeError, ValueError):
                return 0.0
        progress = self._estimate_work_done()
        rem = td - progress
        if rem < 0.0:
            rem = 0.0
        return rem

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not hasattr(self, "_force_on_demand"):
            self._force_on_demand = False

        remaining_work = self._estimate_remaining_work()
        if remaining_work <= 0.0:
            return ClusterType.NONE

        elapsed = getattr(self.env, "elapsed_seconds", 0.0)
        try:
            elapsed = float(elapsed)
        except (TypeError, ValueError):
            elapsed = 0.0

        gap = getattr(self.env, "gap_seconds", 0.0)
        try:
            gap = float(gap)
        except (TypeError, ValueError):
            gap = 0.0
        if gap < 0.0:
            gap = 0.0

        ro_val = getattr(self, "restart_overhead", 0.0)
        try:
            ro = float(ro_val)
        except (TypeError, ValueError):
            ro = 0.0
        if ro < 0.0:
            ro = 0.0

        deadline_val = getattr(self, "deadline", None)
        try:
            deadline = float(deadline_val)
        except (TypeError, ValueError):
            # Unknown deadline: always run on-demand to minimize failure risk.
            self._force_on_demand = True
            return ClusterType.ON_DEMAND

        reserve_time = remaining_work + ro + gap
        latest_safe_start = deadline - reserve_time

        if elapsed >= latest_safe_start:
            self._force_on_demand = True

        if self._force_on_demand:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
