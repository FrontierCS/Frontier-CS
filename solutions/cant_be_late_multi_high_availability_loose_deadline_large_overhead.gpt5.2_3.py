import json
from argparse import Namespace
from typing import Callable, List, Optional, Sequence, Any

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_ema_v1"

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

        self._done_len = 0
        self._done_sum = 0.0
        self._commit_ondemand = False

        self._spot_vec_getter: Optional[Callable[[], Optional[Sequence[bool]]]] = None
        self._spot_ema: Optional[List[float]] = None
        self._ema_alpha = 0.08

        self._switch_cooldown = 0
        self._cooldown_steps = 3

        self._ct_none = getattr(ClusterType, "NONE", None)
        if self._ct_none is None:
            self._ct_none = getattr(ClusterType, "None")

        return self

    def _update_progress_sum(self) -> float:
        lst = self.task_done_time
        n = len(lst)
        if n == self._done_len:
            return self._done_sum
        if n == self._done_len + 1:
            self._done_sum += float(lst[-1])
            self._done_len = n
            return self._done_sum
        # Fallback (should be rare)
        self._done_sum += float(sum(lst[self._done_len : n]))
        self._done_len = n
        return self._done_sum

    def _init_spot_vec_getter(self) -> None:
        env = getattr(self, "env", None)
        if env is None:
            self._spot_vec_getter = lambda: None
            return

        num_regions = None
        try:
            if hasattr(env, "get_num_regions") and callable(env.get_num_regions):
                num_regions = int(env.get_num_regions())
        except Exception:
            num_regions = None

        if not num_regions or num_regions <= 0:
            self._spot_vec_getter = lambda: None
            return

        self._spot_ema = [0.5] * num_regions

        def _valid_vec(v: Any) -> Optional[Sequence[bool]]:
            if isinstance(v, (list, tuple)) and len(v) >= num_regions:
                try:
                    return [bool(v[i]) for i in range(num_regions)]
                except Exception:
                    return None
            return None

        for attr_name in (
            "spot_availabilities",
            "spot_availability",
            "spot_available",
            "spot_avail",
            "has_spot",
            "has_spots",
        ):
            if hasattr(env, attr_name):
                try:
                    v = getattr(env, attr_name)
                    vec = _valid_vec(v)
                    if vec is not None:
                        self._spot_vec_getter = lambda a=attr_name: _valid_vec(getattr(self.env, a))
                        return
                except Exception:
                    pass

        for meth_name in (
            "get_spot_availabilities",
            "get_spot_availability_vector",
            "get_spot_availability",
            "get_spot_available_regions",
            "get_has_spot_vector",
        ):
            fn = getattr(env, meth_name, None)
            if callable(fn):
                # No-arg variant returning vector
                try:
                    v = fn()
                    vec = _valid_vec(v)
                    if vec is not None:
                        self._spot_vec_getter = lambda f=fn: _valid_vec(f())
                        return
                except TypeError:
                    pass
                except Exception:
                    pass

        # Per-region function variant
        for meth_name in (
            "get_spot_availability",
            "get_has_spot",
            "has_spot_in_region",
            "get_spot_available",
            "spot_available_in_region",
        ):
            fn = getattr(env, meth_name, None)
            if callable(fn):
                try:
                    test = fn(0)
                    if isinstance(test, (bool, int)):
                        def _getter(f=fn, n=num_regions):
                            try:
                                return [bool(f(i)) for i in range(n)]
                            except Exception:
                                return None
                        self._spot_vec_getter = _getter
                        return
                except TypeError:
                    pass
                except Exception:
                    pass

        self._spot_vec_getter = lambda: None

    def _maybe_update_ema(self, spot_vec: Optional[Sequence[bool]]) -> None:
        if spot_vec is None or self._spot_ema is None:
            return
        a = self._ema_alpha
        inv = 1.0 - a
        ema = self._spot_ema
        n = min(len(ema), len(spot_vec))
        for i in range(n):
            ema[i] = ema[i] * inv + (1.0 if spot_vec[i] else 0.0) * a

    def _best_spot_region(self, spot_vec: Sequence[bool], cur_region: int) -> Optional[int]:
        if self._spot_ema is None:
            for i, ok in enumerate(spot_vec):
                if ok:
                    return i
            return None
        best = None
        best_score = -1e18
        ema = self._spot_ema
        n = min(len(spot_vec), len(ema))
        for i in range(n):
            if not spot_vec[i]:
                continue
            # Prefer current region to avoid restarts if it is available.
            score = ema[i] + (0.02 if i == cur_region else 0.0)
            if score > best_score:
                best_score = score
                best = i
        return best

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if self._spot_vec_getter is None:
            self._init_spot_vec_getter()

        if self._switch_cooldown > 0:
            self._switch_cooldown -= 1

        progress = self._update_progress_sum()
        remaining_work = float(self.task_duration) - float(progress)
        if remaining_work <= 1e-6:
            return self._ct_none

        elapsed = float(self.env.elapsed_seconds)
        remaining_time = float(self.deadline) - elapsed
        if remaining_time <= 0.0:
            return ClusterType.ON_DEMAND

        gap = float(getattr(self.env, "gap_seconds", 0.0)) or 0.0
        overhead = float(self.restart_overhead)
        pending_overhead = float(getattr(self, "remaining_restart_overhead", 0.0)) or 0.0

        # Conservative "must start/continue on-demand now" rule.
        # Assume: need remaining_work wallclock plus any pending overhead, plus a restart overhead if we aren't already on-demand.
        need = remaining_work + pending_overhead
        if last_cluster_type != ClusterType.ON_DEMAND:
            need += overhead

        buffer = max(3.0 * gap, 3.0 * overhead, 1800.0)  # >= 30 minutes safety
        if remaining_time <= need + buffer:
            self._commit_ondemand = True

        if self._commit_ondemand:
            return ClusterType.ON_DEMAND

        spot_vec = None
        if self._spot_vec_getter is not None:
            try:
                spot_vec = self._spot_vec_getter()
            except Exception:
                spot_vec = None

        self._maybe_update_ema(spot_vec)

        cur_region = 0
        try:
            cur_region = int(self.env.get_current_region())
        except Exception:
            cur_region = 0

        # If spot is allowed, try to ensure we're in a region where spot is actually available (if vector info exists).
        if has_spot:
            if spot_vec is not None:
                if cur_region < len(spot_vec) and not bool(spot_vec[cur_region]):
                    best = self._best_spot_region(spot_vec, cur_region)
                    if best is not None and best != cur_region:
                        try:
                            self.env.switch_region(int(best))
                        except Exception:
                            pass
            return ClusterType.SPOT

        # has_spot is False => cannot return SPOT.
        # If we can see another region has spot (possible mismatch: has_spot might be per-region),
        # switch now and wait this step to be able to use spot next step.
        if spot_vec is not None and self._switch_cooldown <= 0:
            any_spot = any(bool(x) for x in spot_vec)
            if any_spot:
                best = self._best_spot_region(spot_vec, cur_region)
                if best is not None and best != cur_region:
                    try:
                        self.env.switch_region(int(best))
                        self._switch_cooldown = self._cooldown_steps
                    except Exception:
                        pass

        return self._ct_none
