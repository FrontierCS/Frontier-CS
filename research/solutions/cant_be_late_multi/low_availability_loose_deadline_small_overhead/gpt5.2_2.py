import json
import math
from argparse import Namespace
from typing import Any, Callable, List, Optional, Sequence, Tuple

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


def _ct_member(name: str) -> ClusterType:
    m = getattr(ClusterType, name, None)
    if m is not None:
        return m
    for x in ClusterType:
        if getattr(x, "name", "").upper() == name.upper():
            return x
    raise AttributeError(f"ClusterType missing member {name}")


_CT_SPOT = _ct_member("SPOT")
_CT_ON_DEMAND = _ct_member("ON_DEMAND")
_CT_NONE = _ct_member("NONE")


def _as_scalar_seconds(x: Any) -> float:
    if isinstance(x, (list, tuple)):
        if not x:
            return 0.0
        return float(x[0])
    return float(x)


class Solution(MultiRegionStrategy):
    NAME = "cb_late_bandit_v2"

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

        self._rt_init = False
        self._n_regions = 0

        self._task_duration_s = 0.0
        self._deadline_s = 0.0
        self._restart_overhead_s = 0.0

        self._work_done_s = 0.0
        self._last_done_len = 0

        self._beta_a: List[float] = []
        self._beta_b: List[float] = []

        self._no_spot_streak = 0
        self._locked_ondemand = False

        self._peek_all_spot: Optional[Callable[[], Optional[List[bool]]]] = None

        return self

    def _init_runtime(self) -> None:
        if self._rt_init:
            return
        self._rt_init = True

        self._n_regions = int(self.env.get_num_regions())

        self._task_duration_s = _as_scalar_seconds(getattr(self, "task_duration", 0.0))
        self._deadline_s = _as_scalar_seconds(getattr(self, "deadline", 0.0))
        self._restart_overhead_s = _as_scalar_seconds(getattr(self, "restart_overhead", 0.0))

        self._beta_a = [1.0] * self._n_regions
        self._beta_b = [1.0] * self._n_regions

        self._work_done_s = 0.0
        self._last_done_len = 0
        self._no_spot_streak = 0
        self._locked_ondemand = False

        self._peek_all_spot = self._detect_peek_all_spot()

    def _detect_peek_all_spot(self) -> Optional[Callable[[], Optional[List[bool]]]]:
        env = self.env
        n = self._n_regions

        def _normalize_vec(v: Any) -> Optional[List[bool]]:
            if v is None:
                return None
            if isinstance(v, (list, tuple)):
                if len(v) != n:
                    return None
                try:
                    return [bool(x) for x in v]
                except Exception:
                    return None
            return None

        list_method_names = (
            "get_all_has_spot",
            "get_has_spot_all",
            "get_has_spot_all_regions",
            "get_spot_availability",
            "get_spot_availability_all",
            "get_all_spot_availability",
            "get_all_spot_status",
            "spot_availability_all",
        )
        for name in list_method_names:
            f = getattr(env, name, None)
            if callable(f):
                try:
                    v = f()
                except TypeError:
                    continue
                vec = _normalize_vec(v)
                if vec is not None:
                    def _peek(f=f) -> Optional[List[bool]]:
                        try:
                            vv = f()
                        except Exception:
                            return None
                        return _normalize_vec(vv)
                    return _peek

        list_attr_names = (
            "has_spot_all",
            "spot_availability",
            "spot_availability_all",
            "spot_status_all",
            "all_has_spot",
        )
        for name in list_attr_names:
            v = getattr(env, name, None)
            vec = _normalize_vec(v)
            if vec is not None:
                def _peek_attr(name=name) -> Optional[List[bool]]:
                    try:
                        return _normalize_vec(getattr(env, name, None))
                    except Exception:
                        return None
                return _peek_attr

        one_method_names = (
            "has_spot",
            "get_has_spot",
            "is_spot_available",
            "get_spot",
            "get_spot_availability_by_region",
            "get_spot_availability_region",
            "get_region_has_spot",
        )
        for name in one_method_names:
            f = getattr(env, name, None)
            if not callable(f):
                continue
            ok = False
            try:
                r0 = f(0)
                ok = isinstance(r0, (bool, int, float))
            except TypeError:
                ok = False
            except Exception:
                ok = False
            if ok:
                def _peek_one(f=f) -> Optional[List[bool]]:
                    out = [False] * n
                    try:
                        for i in range(n):
                            out[i] = bool(f(i))
                        return out
                    except Exception:
                        return None
                return _peek_one

        return None

    def _update_work_done(self) -> None:
        td = getattr(self, "task_done_time", None)
        if not td:
            return
        if not isinstance(td, list):
            return

        L = len(td)
        if L <= self._last_done_len:
            return

        inc = 0.0
        for x in td[self._last_done_len:]:
            try:
                inc += float(x)
            except Exception:
                pass
        self._work_done_s += inc
        self._last_done_len = L

    def _region_score(self, i: int) -> float:
        a = self._beta_a[i]
        b = self._beta_b[i]
        denom = a + b
        mean = a / denom
        explore = 0.35 / math.sqrt(denom)
        return mean + explore

    def _pick_best_region(self, prefer_spot_vec: Optional[List[bool]] = None) -> int:
        cur = int(self.env.get_current_region())
        best_i = cur
        best_s = -1e18

        if prefer_spot_vec is not None:
            for i in range(self._n_regions):
                if not prefer_spot_vec[i]:
                    continue
                s = self._region_score(i)
                if s > best_s:
                    best_s = s
                    best_i = i
            if best_s > -1e17:
                return best_i

        for i in range(self._n_regions):
            s = self._region_score(i)
            if s > best_s:
                best_s = s
                best_i = i
        return best_i

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._init_runtime()
        self._update_work_done()

        remaining_work = self._task_duration_s - self._work_done_s
        if remaining_work <= 0:
            return _CT_NONE

        now = float(getattr(self.env, "elapsed_seconds", 0.0))
        time_left = self._deadline_s - now
        if time_left <= 0:
            return _CT_NONE

        gap = float(getattr(self.env, "gap_seconds", 0.0)) or 1.0
        ro = self._restart_overhead_s
        pending_ro = float(getattr(self, "remaining_restart_overhead", 0.0) or 0.0)

        cur_region = int(self.env.get_current_region())

        spot_vec: Optional[List[bool]] = None
        if self._peek_all_spot is not None:
            spot_vec = self._peek_all_spot()

        if spot_vec is not None and len(spot_vec) == self._n_regions:
            for i, s in enumerate(spot_vec):
                if s:
                    self._beta_a[i] += 1.0
                else:
                    self._beta_b[i] += 1.0
            cur_has_spot = bool(spot_vec[cur_region])
        else:
            cur_has_spot = bool(has_spot)
            if cur_has_spot:
                self._beta_a[cur_region] += 1.0
            else:
                self._beta_b[cur_region] += 1.0

        if cur_has_spot:
            self._no_spot_streak = 0
        else:
            self._no_spot_streak += 1

        overhead_budget = time_left - remaining_work
        safety = max(4.0 * ro, 0.10 * gap)

        if overhead_budget <= safety + 1.1 * ro:
            self._locked_ondemand = True

        if self._locked_ondemand:
            return _CT_ON_DEMAND

        def allow_idle_step() -> bool:
            if overhead_budget < gap + safety:
                return False
            if pending_ro > 0.0 and overhead_budget < gap + safety + pending_ro:
                return False
            return True

        if spot_vec is not None:
            any_spot = any(spot_vec)
            if any_spot:
                if last_cluster_type == _CT_ON_DEMAND:
                    if overhead_budget >= (2.0 * gap + 6.0 * ro + safety):
                        target = self._pick_best_region(prefer_spot_vec=spot_vec)
                        if target != cur_region:
                            self.env.switch_region(int(target))
                        return _CT_SPOT
                    return _CT_ON_DEMAND

                target = self._pick_best_region(prefer_spot_vec=spot_vec)
                if target != cur_region:
                    self.env.switch_region(int(target))
                return _CT_SPOT

            if allow_idle_step():
                if self._no_spot_streak >= 2:
                    target = self._pick_best_region()
                    if target != cur_region:
                        self.env.switch_region(int(target))
                return _CT_NONE

            return _CT_ON_DEMAND

        if cur_has_spot:
            if last_cluster_type == _CT_ON_DEMAND and overhead_budget < (2.0 * gap + 6.0 * ro + safety):
                return _CT_ON_DEMAND
            return _CT_SPOT

        if allow_idle_step():
            if self._no_spot_streak >= 2:
                target = self._pick_best_region()
                if target != cur_region:
                    self.env.switch_region(int(target))
            return _CT_NONE

        return _CT_ON_DEMAND