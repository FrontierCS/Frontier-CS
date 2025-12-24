import json
from argparse import Namespace
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "mr_deadline_guard_v1"

    def solve(self, spec_path: str) -> "Solution":
        with open(spec_path) as f:
            config = json.load(f)

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)

        self._done_cache = 0.0
        self._done_len = 0

        self._inited = False
        self._num_regions = 0
        self._region_scores: List[float] = []
        self._ema_alpha = 0.985

        self._spot_query: Optional[Callable[[], Optional[List[bool]]]] = None
        self._locked_on_demand = False

        return self

    def _is_bool_seq(self, obj: Any, n: int) -> bool:
        if obj is None:
            return False
        if isinstance(obj, (str, bytes, bytearray)):
            return False
        if isinstance(obj, dict):
            if len(obj) != n:
                return False
            for i in range(n):
                if i not in obj:
                    return False
            return True
        try:
            ln = len(obj)  # type: ignore[arg-type]
        except Exception:
            return False
        if ln != n:
            return False
        try:
            it = iter(obj)  # type: ignore[arg-type]
            for _ in range(min(n, 3)):
                next(it)
        except Exception:
            return False
        return True

    def _normalize_avails(self, obj: Any, n: int) -> Optional[List[bool]]:
        if obj is None:
            return None
        if isinstance(obj, dict):
            try:
                return [bool(obj[i]) for i in range(n)]
            except Exception:
                return None
        try:
            if hasattr(obj, "tolist"):
                obj = obj.tolist()
        except Exception:
            pass
        try:
            if not self._is_bool_seq(obj, n):
                return None
            return [bool(x) for x in list(obj)]
        except Exception:
            return None

    def _detect_spot_query(self) -> Optional[Callable[[], Optional[List[bool]]]]:
        env = self.env
        n = env.get_num_regions()

        attr_candidates = (
            "spot_availabilities",
            "spot_availability",
            "has_spot_all",
            "has_spot_by_region",
            "spot_by_region",
            "spot",
            "spot_status",
            "spot_status_by_region",
            "region_spot_availability",
            "region_has_spot",
        )
        for attr in attr_candidates:
            try:
                if hasattr(env, attr):
                    v = getattr(env, attr)
                    av = self._normalize_avails(v, n)
                    if av is not None:
                        return lambda attr=attr, n=n: self._normalize_avails(getattr(self.env, attr, None), n)
            except Exception:
                continue

        method_candidates: Tuple[str, ...] = (
            "get_spot_availabilities",
            "get_spot_availability",
            "get_spot_status",
            "get_spot_by_region",
            "get_has_spot_by_region",
            "get_region_has_spot",
            "get_region_spot_availability",
            "has_spot_by_region",
            "spot_availability_by_region",
            "spot_avail_by_region",
        )
        for name in method_candidates:
            m = getattr(env, name, None)
            if not callable(m):
                continue
            # No-arg: returns list/dict
            try:
                r = m()
                av = self._normalize_avails(r, n)
                if av is not None:
                    return lambda name=name, n=n: self._normalize_avails(getattr(self.env, name)(), n)
            except TypeError:
                pass
            except Exception:
                continue

            # (idx)->bool
            try:
                r0 = m(0)
                if isinstance(r0, (bool, int)):
                    return lambda name=name, n=n: [bool(getattr(self.env, name)(i)) for i in range(n)]
            except TypeError:
                pass
            except Exception:
                continue

        return None

    def _ensure_init(self) -> None:
        if self._inited:
            return
        self._num_regions = int(self.env.get_num_regions())
        self._region_scores = [0.5] * self._num_regions
        self._spot_query = self._detect_spot_query()
        self._locked_on_demand = False
        self._inited = True

    def _update_done_cache(self) -> None:
        td = self.task_done_time
        new_len = len(td)
        if new_len <= self._done_len:
            return
        if new_len == self._done_len + 1:
            self._done_cache += float(td[-1])
        else:
            self._done_cache += float(sum(td[self._done_len : new_len]))
        self._done_len = new_len

    def _get_all_spot_avails(self) -> Optional[List[bool]]:
        if self._spot_query is None:
            return None
        try:
            av = self._spot_query()
            if av is None:
                return None
            if len(av) != self._num_regions:
                return None
            return av
        except Exception:
            self._spot_query = None
            return None

    def _pick_best_spot_region(self, avails: List[bool], cur: int) -> int:
        if avails[cur]:
            return cur
        best = cur
        best_score = -1.0
        cur_score = self._region_scores[cur] if 0 <= cur < self._num_regions else 0.0
        for i, a in enumerate(avails):
            if not a:
                continue
            s = self._region_scores[i]
            if s > best_score + 1e-12:
                best_score = s
                best = i
            elif abs(s - best_score) <= 1e-12:
                if abs(i - cur) < abs(best - cur):
                    best = i
                elif abs(i - cur) == abs(best - cur) and s >= cur_score and i < best:
                    best = i
        return best

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_init()
        self._update_done_cache()

        if self._done_cache >= self.task_duration - 1e-9:
            return ClusterType.NONE

        env = self.env
        gap = float(env.gap_seconds)
        over = float(self.restart_overhead)

        remaining_time = float(self.deadline) - float(env.elapsed_seconds)
        remaining_work = float(self.task_duration) - float(self._done_cache)

        if remaining_time <= 1e-9:
            return ClusterType.NONE

        slack = remaining_time - remaining_work
        req_util = remaining_work / max(remaining_time, 1e-9)

        # Lock to on-demand late in the horizon to avoid deadline miss.
        lock_slack = gap + 2.0 * over
        if (slack <= lock_slack) or (req_util >= 0.97):
            self._locked_on_demand = True

        avails = self._get_all_spot_avails()

        cur_region = int(env.get_current_region())
        local_has_spot = bool(has_spot)

        if avails is not None:
            a = 1.0 - self._ema_alpha
            for i, ok in enumerate(avails):
                self._region_scores[i] = self._region_scores[i] * self._ema_alpha + a * (1.0 if ok else 0.0)

            if any(avails):
                best_region = self._pick_best_spot_region(avails, cur_region)

                # Avoid resetting a partially-consumed restart overhead by switching.
                allow_switch = True
                try:
                    rro = float(self.remaining_restart_overhead)
                    if rro > 1e-9 and rro < 0.90 * over:
                        allow_switch = False
                except Exception:
                    allow_switch = True

                if (best_region != cur_region) and allow_switch and (not self._locked_on_demand):
                    try:
                        env.switch_region(best_region)
                        cur_region = best_region
                    except Exception:
                        pass

                local_has_spot = bool(avails[cur_region])
            else:
                local_has_spot = False
        else:
            # Update current-region score only.
            a = 1.0 - self._ema_alpha
            if 0 <= cur_region < self._num_regions:
                self._region_scores[cur_region] = self._region_scores[cur_region] * self._ema_alpha + a * (
                    1.0 if local_has_spot else 0.0
                )

        if self._locked_on_demand:
            return ClusterType.ON_DEMAND

        if local_has_spot:
            return ClusterType.SPOT

        # No spot (in current region, and across regions if we could observe it).
        # Decide between waiting and on-demand based on urgency.
        if req_util >= 0.80:
            return ClusterType.ON_DEMAND

        # If we can afford to wait at least one gap without forcing later on-demand, do so.
        if slack > (gap + 2.0 * over):
            return ClusterType.NONE

        return ClusterType.ON_DEMAND
