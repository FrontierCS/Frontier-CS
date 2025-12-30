import json
from argparse import Namespace
from typing import Callable, List, Optional, Sequence, Any

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


def _cluster_none() -> ClusterType:
    if hasattr(ClusterType, "NONE"):
        return ClusterType.NONE  # type: ignore[attr-defined]
    try:
        return ClusterType["None"]  # type: ignore[index]
    except Exception:
        return ClusterType.NONE  # type: ignore[attr-defined]


_CT_NONE = _cluster_none()
_CT_SPOT = ClusterType.SPOT
_CT_OD = ClusterType.ON_DEMAND


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_region_aware_v1"

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

        self._initialized = False
        self._last_elapsed = -1.0

        self._total_task_duration = None
        self._deadline_seconds = None
        self._restart_overhead_seconds = None

        self._done_total = 0.0
        self._done_len = 0

        self._committed_od = False

        self._num_regions = None
        self._ema = None
        self._ema_alpha = 0.05

        self._gap_seconds = None
        self._buffer_seconds = None

        self._all_region_spot_query = None
        self._current_region_spot_query = None

        return self

    def _reset_internal(self) -> None:
        self._initialized = False
        self._done_total = 0.0
        self._done_len = 0
        self._committed_od = False
        self._last_elapsed = -1.0
        self._all_region_spot_query = None
        self._current_region_spot_query = None
        self._num_regions = None
        self._ema = None
        self._gap_seconds = None
        self._buffer_seconds = None

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return

        env = getattr(self, "env", None)
        if env is None:
            return

        # Cache key params
        self._gap_seconds = float(getattr(env, "gap_seconds", 0.0) or 0.0)

        td = getattr(self, "task_duration", None)
        if isinstance(td, (list, tuple)):
            total_td = float(sum(float(x) for x in td))
        else:
            total_td = float(td) if td is not None else 0.0
        self._total_task_duration = total_td

        self._deadline_seconds = float(getattr(self, "deadline", 0.0) or 0.0)
        self._restart_overhead_seconds = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        # Buffer: be safe near the end to avoid deadline miss due to step granularity / overhead interactions.
        gap = self._gap_seconds
        oh = self._restart_overhead_seconds
        self._buffer_seconds = max(0.25 * gap, 2.0 * oh, 1.0)

        # Region info
        try:
            self._num_regions = int(env.get_num_regions())
        except Exception:
            self._num_regions = 1
        n = self._num_regions
        self._ema = [0.5] * n

        self._detect_spot_queries()

        self._initialized = True

    def _detect_spot_queries(self) -> None:
        env = self.env
        n = self._num_regions or 1

        def _is_boolish(x: Any) -> bool:
            return isinstance(x, (bool, int)) and (x is True or x is False or x in (0, 1))

        # All-region spot query
        all_list_method_names = (
            "get_spot_availabilities",
            "get_spot_availability",
            "get_all_spot_availability",
            "get_all_spot_availabilities",
            "spot_availabilities",
            "spot_availability",
        )
        all_idx_method_names = (
            "get_spot_availability",
            "get_has_spot",
            "has_spot_in_region",
            "is_spot_available",
            "spot_available",
        )
        all_attr_names = (
            "spot_availabilities",
            "spot_availability",
            "has_spot_by_region",
            "spot_by_region",
        )

        # Try methods returning a full list
        for name in all_list_method_names:
            m = getattr(env, name, None)
            if callable(m):
                try:
                    v = m()
                except TypeError:
                    continue
                except Exception:
                    continue
                if isinstance(v, (list, tuple)) and len(v) == n and all(_is_boolish(x) for x in v):
                    self._all_region_spot_query = lambda m=m: [bool(x) for x in m()]
                    break
        # Try methods taking idx
        if self._all_region_spot_query is None:
            for name in all_idx_method_names:
                m = getattr(env, name, None)
                if callable(m):
                    try:
                        v = m(0)
                    except TypeError:
                        continue
                    except Exception:
                        continue
                    if _is_boolish(v):
                        self._all_region_spot_query = lambda m=m, n=n: [bool(m(i)) for i in range(n)]
                        break
        # Try attribute list
        if self._all_region_spot_query is None:
            for name in all_attr_names:
                v = getattr(env, name, None)
                if isinstance(v, (list, tuple)) and len(v) == n and all(_is_boolish(x) for x in v):
                    self._all_region_spot_query = lambda name=name, env=env: [bool(x) for x in getattr(env, name)]
                    break

        # Current-region spot query (for scanning if we can't query all regions)
        curr_method_names = (
            "get_has_spot",
            "has_spot",
            "get_current_has_spot",
            "is_spot_available",
            "spot_available",
        )
        curr_attr_names = (
            "has_spot",
            "spot_available",
            "current_has_spot",
        )

        for name in curr_method_names:
            m = getattr(env, name, None)
            if callable(m):
                try:
                    v = m()
                except TypeError:
                    continue
                except Exception:
                    continue
                if _is_boolish(v):
                    self._current_region_spot_query = lambda m=m: bool(m())
                    break

        if self._current_region_spot_query is None:
            for name in curr_attr_names:
                v = getattr(env, name, None)
                if _is_boolish(v):
                    self._current_region_spot_query = lambda name=name, env=env: bool(getattr(env, name))
                    break

    def _update_done_cache(self) -> float:
        lst = getattr(self, "task_done_time", None)
        if not isinstance(lst, list):
            return 0.0
        n = len(lst)
        if n < self._done_len:
            self._done_total = 0.0
            self._done_len = 0
        if n > self._done_len:
            self._done_total += float(sum(float(x) for x in lst[self._done_len : n]))
            self._done_len = n
        return self._done_total

    def _get_all_region_spot(self) -> Optional[List[bool]]:
        q = self._all_region_spot_query
        if q is None:
            return None
        try:
            v = q()
            if isinstance(v, list):
                return v
            if isinstance(v, tuple):
                return list(v)
            return None
        except Exception:
            return None

    def _select_best_spot_region(self, spot_list: Sequence[bool], current_region: int) -> Optional[int]:
        best = None
        best_score = -1e18
        ema = self._ema or []
        for i, avail in enumerate(spot_list):
            if not avail:
                continue
            s = (ema[i] if i < len(ema) else 0.5)
            if i == current_region:
                s += 1e-6
            if s > best_score:
                best_score = s
                best = i
        return best

    def _maybe_switch_to_spot_region(self, has_spot_current: bool) -> bool:
        env = self.env
        try:
            cur = int(env.get_current_region())
        except Exception:
            cur = 0

        if has_spot_current:
            return True

        # If switching is extremely inefficient relative to step size, avoid it.
        gap = float(self._gap_seconds or 0.0)
        oh = float(self._restart_overhead_seconds or 0.0)
        # Known spot/on-demand ratio from the prompt:
        # spot_price / od_price ~= 0.9701 / 3.06 = 0.317
        # Switching+restart yields productive fraction f ~ max(0, (gap-oh)/gap).
        # Prefer switching only if effective spot per productive work still cheaper than OD:
        # f > 0.317  =>  oh < 0.683*gap
        if gap > 0.0 and oh >= 0.683 * gap:
            return False

        spot_list = self._get_all_region_spot()
        if spot_list is not None:
            # Update EMA for all regions
            alpha = self._ema_alpha
            ema = self._ema or [0.5] * len(spot_list)
            if len(ema) != len(spot_list):
                ema = [0.5] * len(spot_list)
                self._ema = ema
            for i, a in enumerate(spot_list):
                ema[i] = (1.0 - alpha) * ema[i] + alpha * (1.0 if a else 0.0)

            best = self._select_best_spot_region(spot_list, cur)
            if best is None:
                return False
            if best != cur:
                try:
                    env.switch_region(best)
                except Exception:
                    return False
            return True

        # No all-region query; attempt to scan by switching if we can query current region spot.
        qcur = self._current_region_spot_query
        if qcur is None:
            return False

        n = self._num_regions or 1
        alpha = self._ema_alpha
        ema = self._ema or [0.5] * n
        if len(ema) != n:
            ema = [0.5] * n
            self._ema = ema

        # Candidate order: try higher EMA first, but test current region first to avoid unnecessary switches.
        order = list(range(n))
        order.sort(key=lambda i: ema[i], reverse=True)
        if cur in order:
            order.remove(cur)
        order.insert(0, cur)

        orig = cur
        found = None
        for r in order:
            if r != cur:
                try:
                    env.switch_region(r)
                    cur = r
                except Exception:
                    continue
            try:
                avail = bool(qcur())
            except Exception:
                avail = False
            # Update EMA for tested region
            ema[r] = (1.0 - alpha) * ema[r] + alpha * (1.0 if avail else 0.0)
            if avail:
                found = r
                break

        if found is None:
            if cur != orig:
                try:
                    env.switch_region(orig)
                except Exception:
                    pass
            return False
        return True

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_initialized()
        env = self.env

        now = float(getattr(env, "elapsed_seconds", 0.0) or 0.0)
        if self._last_elapsed >= 0.0 and now < self._last_elapsed:
            self._reset_internal()
            self._ensure_initialized()
            env = self.env
            now = float(getattr(env, "elapsed_seconds", 0.0) or 0.0)
        self._last_elapsed = now

        done = self._update_done_cache()
        total = float(self._total_task_duration or 0.0)
        remaining_work = total - done
        if remaining_work <= 1e-9:
            return _CT_NONE

        deadline = float(self._deadline_seconds or 0.0)
        remaining_time = deadline - now
        if remaining_time <= 0.0:
            return _CT_NONE

        if self._committed_od:
            return _CT_OD

        # Decide if we must commit to on-demand to guarantee completion.
        # Conservative: assume switching to OD incurs a full restart overhead unless already on OD.
        if last_cluster_type == _CT_OD:
            overhead_needed = float(getattr(self, "remaining_restart_overhead", 0.0) or 0.0)
        else:
            overhead_needed = float(self._restart_overhead_seconds or 0.0)

        buffer_s = float(self._buffer_seconds or 0.0)
        if remaining_time <= remaining_work + overhead_needed + buffer_s:
            self._committed_od = True
            return _CT_OD

        # Prefer spot if we can run it (possibly by switching regions).
        if has_spot:
            # Update EMA for current region if we don't have all-region view.
            if self._all_region_spot_query is None and self._ema is not None:
                try:
                    cur = int(env.get_current_region())
                except Exception:
                    cur = 0
                if 0 <= cur < len(self._ema):
                    a = self._ema_alpha
                    self._ema[cur] = (1.0 - a) * self._ema[cur] + a * 1.0
            return _CT_SPOT

        # Spot not available in current region.
        # Update EMA for current region if we don't have all-region view.
        if self._all_region_spot_query is None and self._ema is not None:
            try:
                cur = int(env.get_current_region())
            except Exception:
                cur = 0
            if 0 <= cur < len(self._ema):
                a = self._ema_alpha
                self._ema[cur] = (1.0 - a) * self._ema[cur] + a * 0.0

        if self._maybe_switch_to_spot_region(False):
            # If we successfully moved to a spot-available region, run spot.
            # When using scanning-based switching, ensure spot really exists now.
            if self._all_region_spot_query is None and self._current_region_spot_query is not None:
                try:
                    if not bool(self._current_region_spot_query()):
                        return _CT_NONE
                except Exception:
                    return _CT_NONE
            return _CT_SPOT

        # Otherwise, wait (use slack) and avoid on-demand until necessary.
        return _CT_NONE