import json
import inspect
from argparse import Namespace
from typing import Callable, Optional, Tuple, Any, List

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_multiregion_v1"

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

        self._state_init = False
        return self

    @staticmethod
    def _to_scalar(x: Any) -> float:
        if isinstance(x, (list, tuple)):
            return float(x[0]) if x else 0.0
        return float(x)

    def _ensure_state(self) -> None:
        if getattr(self, "_state_init", False):
            return
        self._state_init = True

        self._done_sum = 0.0
        self._done_len = 0

        n = int(self.env.get_num_regions())
        self._spot_true = [0] * n
        self._spot_total = [0] * n

        self._rr_region = 0
        self._force_od = False

        self._task_duration_sec = self._to_scalar(self.task_duration)
        self._deadline_sec = self._to_scalar(self.deadline)
        self._restart_overhead_sec = self._to_scalar(self.restart_overhead)

        self._probe = None  # type: Optional[Callable[..., bool]]
        self._probe_takes_idx = False
        self._discover_spot_probe()

    def _update_done_sum(self) -> float:
        tdt = self.task_done_time
        l = len(tdt)
        if l != self._done_len:
            self._done_sum += sum(tdt[self._done_len : l])
            self._done_len = l
        return self._done_sum

    def _discover_spot_probe(self) -> None:
        env = self.env

        def _try_method(name: str) -> Optional[Tuple[Callable[..., bool], bool]]:
            attr = getattr(env, name, None)
            if attr is None:
                return None

            if isinstance(attr, bool):
                def _f() -> bool:
                    return bool(getattr(self.env, name))
                return (_f, False)

            if callable(attr):
                try:
                    sig = inspect.signature(attr)
                    nparams = len(sig.parameters)
                except Exception:
                    nparams = None

                if nparams == 0:
                    def _f0(a=attr) -> bool:
                        return bool(a())
                    try:
                        _ = _f0()
                        return (_f0, False)
                    except Exception:
                        return None

                if nparams == 1:
                    def _f1(idx: int, a=attr) -> bool:
                        return bool(a(idx))
                    try:
                        _ = _f1(int(self.env.get_current_region()))
                        return (_f1, True)
                    except Exception:
                        return None

            return None

        # Methods/attrs that might exist.
        for name in (
            "get_has_spot",
            "has_spot",
            "spot_available",
            "get_spot_availability",
            "current_has_spot",
            "is_spot_available",
        ):
            res = _try_method(name)
            if res is not None:
                self._probe, self._probe_takes_idx = res
                return

        # Array-like availability for all regions at current timestep.
        for name in (
            "spot_availability",
            "spot_availabilities",
            "has_spot_per_region",
            "spot_per_region",
        ):
            arr = getattr(env, name, None)
            if isinstance(arr, (list, tuple)):
                def _fa(idx: int, n=name) -> bool:
                    a = getattr(self.env, n)
                    if 0 <= idx < len(a):
                        return bool(a[idx])
                    return False
                try:
                    _ = _fa(int(self.env.get_current_region()))
                    self._probe, self._probe_takes_idx = _fa, True
                    return
                except Exception:
                    pass

        self._probe = None
        self._probe_takes_idx = False

    def _spot_score(self, idx: int) -> float:
        # Laplace smoothing
        t = self._spot_total[idx]
        s = self._spot_true[idx]
        return (s + 1.0) / (t + 2.0)

    def _probe_has_spot_in_region(self, idx: int) -> Optional[bool]:
        if self._probe is None:
            return None
        try:
            if self._probe_takes_idx:
                return bool(self._probe(int(idx)))
            # probe for current region only
            cur = int(self.env.get_current_region())
            if cur != int(idx):
                return None
            return bool(self._probe())
        except Exception:
            self._probe = None
            self._probe_takes_idx = False
            return None

    def _find_spot_region_now(self, allow_switch_scan: bool) -> Optional[int]:
        n = int(self.env.get_num_regions())
        if self._probe is None:
            return None

        if self._probe_takes_idx:
            best_idx = None
            best_score = -1.0
            for i in range(n):
                v = self._probe_has_spot_in_region(i)
                if v:
                    sc = self._spot_score(i)
                    if sc > best_score:
                        best_score = sc
                        best_idx = i
            return best_idx

        if not allow_switch_scan:
            return None

        orig = int(self.env.get_current_region())
        best_idx = None
        best_score = -1.0
        for i in range(n):
            if i != int(self.env.get_current_region()):
                self.env.switch_region(i)
            v = self._probe_has_spot_in_region(i)
            if v:
                sc = self._spot_score(i)
                if sc > best_score:
                    best_score = sc
                    best_idx = i
        if best_idx is None:
            if int(self.env.get_current_region()) != orig:
                self.env.switch_region(orig)
            return None
        if int(self.env.get_current_region()) != best_idx:
            self.env.switch_region(best_idx)
        return best_idx

    def _best_wait_region(self) -> int:
        n = int(self.env.get_num_regions())
        best_idx = 0
        best_score = -1.0
        for i in range(n):
            sc = self._spot_score(i)
            if sc > best_score:
                best_score = sc
                best_idx = i
        return best_idx

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_state()

        cur_region = int(self.env.get_current_region())
        self._spot_total[cur_region] += 1
        if has_spot:
            self._spot_true[cur_region] += 1

        done = self._update_done_sum()
        remaining_work = self._task_duration_sec - done
        if remaining_work <= 0:
            return ClusterType.NONE

        elapsed = float(self.env.elapsed_seconds)
        time_left = self._deadline_sec - elapsed
        if time_left <= 0:
            return ClusterType.NONE

        gap = float(self.env.gap_seconds)
        over = self._restart_overhead_sec
        rem_over = float(getattr(self, "remaining_restart_overhead", 0.0) or 0.0)

        # Minimum time-to-finish if we run ON_DEMAND continuously from now (no further switches).
        start_over_od = rem_over if last_cluster_type == ClusterType.ON_DEMAND else over
        min_time_od = remaining_work + max(0.0, start_over_od)

        hard_margin = max(2.0 * over, gap)
        if (not self._force_od) and (time_left <= min_time_od + hard_margin):
            self._force_od = True

        # If overhead is still being paid down, avoid switching to prevent resetting it.
        if rem_over > 0.0:
            if self._force_od:
                return ClusterType.ON_DEMAND
            if last_cluster_type == ClusterType.ON_DEMAND:
                return ClusterType.ON_DEMAND
            if last_cluster_type == ClusterType.SPOT and has_spot:
                return ClusterType.SPOT
            # Can't keep SPOT; decide wait vs OD without switching regions.
            slack = time_left - min_time_od
            wait_slack = max(6.0 * gap, 4.0 * over)
            if last_cluster_type != ClusterType.ON_DEMAND and slack > wait_slack:
                return ClusterType.NONE
            return ClusterType.ON_DEMAND

        if self._force_od:
            return ClusterType.ON_DEMAND

        slack = time_left - min_time_od

        # If currently on ON_DEMAND, generally keep it, optionally switch to spot if safe and available.
        if last_cluster_type == ClusterType.ON_DEMAND:
            if has_spot:
                switch_slack = max(4.0 * over, 3.0 * gap)
                if slack > switch_slack:
                    return ClusterType.SPOT
            return ClusterType.ON_DEMAND

        # Not on ON_DEMAND: prioritize SPOT if we can.
        if has_spot:
            return ClusterType.SPOT

        # Try to find a region with spot now (safe probing only).
        allow_switch_scan = (last_cluster_type != ClusterType.ON_DEMAND)
        spot_region = self._find_spot_region_now(allow_switch_scan=allow_switch_scan)
        if spot_region is not None:
            # If probe required switch scan, region already set; otherwise switch now.
            if int(self.env.get_current_region()) != int(spot_region):
                self.env.switch_region(int(spot_region))
            # Must be sure spot exists in final region; probe by idx guarantees this.
            if self._probe_takes_idx:
                if self._probe_has_spot_in_region(int(spot_region)):
                    return ClusterType.SPOT
            else:
                # Probe uses current region; we've switched there.
                v = self._probe_has_spot_in_region(int(spot_region))
                if v:
                    return ClusterType.SPOT

        # No spot available now. Decide wait vs OD.
        wait_slack = max(6.0 * gap, 4.0 * over)
        if slack > wait_slack:
            # While waiting, optionally reposition to a better region for next step.
            # Only switch when not paying overhead (rem_over==0 here).
            if self._probe is not None and self._probe_takes_idx:
                best = self._best_wait_region()
                if best != int(self.env.get_current_region()):
                    self.env.switch_region(best)
            else:
                # Blind exploration: switch regions round-robin while idle.
                n = int(self.env.get_num_regions())
                if n > 1:
                    nxt = (int(self.env.get_current_region()) + 1) % n
                    self.env.switch_region(nxt)
            return ClusterType.NONE

        return ClusterType.ON_DEMAND