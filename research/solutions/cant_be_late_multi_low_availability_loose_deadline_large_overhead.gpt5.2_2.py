import json
from argparse import Namespace
from typing import Callable, List, Optional

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "deadline_safe_spot_v1"

    def solve(self, spec_path: str) -> "Solution":
        with open(spec_path, "r") as f:
            config = json.load(f)

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)

        self._final_phase = False

        self._done_sum = 0.0
        self._done_len = 0

        self._lazy_inited = False
        self._final_buffer_s = None

        self._spot_query_multi: Optional[Callable[[], List[bool]]] = None
        self._spot_query_checked = False

        self._ema: Optional[List[float]] = None
        self._ema_alpha = 0.02

        self._last_region_switch_elapsed = -1e30
        self._min_switch_interval_s = None
        return self

    def _ensure_lazy_init(self) -> None:
        if self._lazy_inited:
            return
        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        overhead = float(self.restart_overhead)
        self._final_buffer_s = max(2.0 * gap, 4.0 * overhead)
        self._min_switch_interval_s = 10.0 * gap if gap > 0 else 0.0

        n = int(self.env.get_num_regions())
        self._ema = [0.5] * n
        self._lazy_inited = True

    def _update_done_sum(self) -> float:
        td = self.task_done_time
        if td is None:
            self._done_sum = 0.0
            self._done_len = 0
            return 0.0
        cur_len = len(td)
        if cur_len < self._done_len:
            self._done_sum = float(sum(td))
            self._done_len = cur_len
            return self._done_sum
        if cur_len == self._done_len:
            return self._done_sum
        s = self._done_sum
        for i in range(self._done_len, cur_len):
            s += float(td[i])
        self._done_sum = s
        self._done_len = cur_len
        return s

    def _detect_spot_query_multi(self) -> None:
        if self._spot_query_checked:
            return
        self._spot_query_checked = True

        env = self.env
        n = int(env.get_num_regions())

        cand_multi = [
            "get_spot_availabilities",
            "get_all_spot_availabilities",
            "get_all_has_spot",
            "get_has_spot_all_regions",
            "spot_availabilities",
            "has_spot_all_regions",
            "all_has_spot",
        ]
        for name in cand_multi:
            if hasattr(env, name):
                attr = getattr(env, name)
                if callable(attr):
                    try:
                        v = attr()
                    except TypeError:
                        continue
                    except Exception:
                        continue
                    if isinstance(v, (list, tuple)) and len(v) == n:
                        def _q(attr=attr, n=n):
                            x = attr()
                            if not isinstance(x, (list, tuple)) or len(x) != n:
                                return None
                            return [bool(t) for t in x]
                        self._spot_query_multi = _q
                        return
                else:
                    v = attr
                    if isinstance(v, (list, tuple)) and len(v) == n:
                        def _q(name=name, n=n):
                            x = getattr(self.env, name, None)
                            if not isinstance(x, (list, tuple)) or len(x) != n:
                                return None
                            return [bool(t) for t in x]
                        self._spot_query_multi = _q
                        return

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_lazy_init()
        self._detect_spot_query_multi()

        done = self._update_done_sum()
        if done >= self.task_duration - 1e-9:
            return ClusterType.NONE

        rem_work = self.task_duration - done
        rem_time = self.deadline - float(self.env.elapsed_seconds)

        if rem_time <= 0:
            return ClusterType.NONE

        if (not self._final_phase) and (rem_time <= rem_work + float(self._final_buffer_s)):
            self._final_phase = True

        if self._final_phase:
            return ClusterType.ON_DEMAND

        # Spot-preferred phase: run spot when available, otherwise pause.
        # Optional: when spot is unavailable, if we can observe other regions' spot availability,
        # switch to a region that currently has spot to improve chances next step.
        if not has_spot:
            if self._spot_query_multi is not None and self._ema is not None:
                avail = self._spot_query_multi()
                if avail is not None:
                    n = len(avail)
                    a = float(self._ema_alpha)
                    for i in range(n):
                        self._ema[i] = (1.0 - a) * self._ema[i] + a * (1.0 if avail[i] else 0.0)

                    cur_region = int(self.env.get_current_region())
                    if (self._min_switch_interval_s is not None and
                            float(self.env.elapsed_seconds) - self._last_region_switch_elapsed >= float(self._min_switch_interval_s)):
                        best = -1
                        best_score = -1.0
                        for i in range(n):
                            if avail[i] and self._ema[i] > best_score:
                                best_score = self._ema[i]
                                best = i
                        if best >= 0 and best != cur_region:
                            try:
                                self.env.switch_region(best)
                                self._last_region_switch_elapsed = float(self.env.elapsed_seconds)
                            except Exception:
                                pass
            return ClusterType.NONE

        # has_spot == True
        if self._spot_query_multi is not None and self._ema is not None:
            avail = self._spot_query_multi()
            if avail is not None:
                n = len(avail)
                a = float(self._ema_alpha)
                for i in range(n):
                    self._ema[i] = (1.0 - a) * self._ema[i] + a * (1.0 if avail[i] else 0.0)

                cur_region = int(self.env.get_current_region())
                if avail[cur_region]:
                    cur_score = self._ema[cur_region]
                else:
                    cur_score = -1.0

                if (self._min_switch_interval_s is not None and
                        float(self.env.elapsed_seconds) - self._last_region_switch_elapsed >= float(self._min_switch_interval_s)):
                    best = cur_region
                    best_score = cur_score
                    for i in range(n):
                        if avail[i] and self._ema[i] > best_score + 0.05:
                            best_score = self._ema[i]
                            best = i
                    if best != cur_region and avail[best]:
                        try:
                            self.env.switch_region(best)
                            self._last_region_switch_elapsed = float(self.env.elapsed_seconds)
                        except Exception:
                            pass

        return ClusterType.SPOT