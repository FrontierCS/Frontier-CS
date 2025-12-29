import json
from argparse import Namespace
from typing import Callable, Optional, List, Any

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


def _get_cluster_type_attr(name: str) -> ClusterType:
    return getattr(ClusterType, name)


CT_SPOT = _get_cluster_type_attr("SPOT")
CT_ON_DEMAND = _get_cluster_type_attr("ON_DEMAND") if hasattr(ClusterType, "ON_DEMAND") else _get_cluster_type_attr("ONDEMAND")
CT_NONE = _get_cluster_type_attr("NONE") if hasattr(ClusterType, "NONE") else getattr(ClusterType, "None")


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_mr_v1"

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

        self._done_accum = 0.0
        self._last_done_len = 0

        self._num_regions = None
        self._ema = None
        self._streak_avail = None
        self._streak_unavail = None

        self._spot_reader = None  # type: Optional[Callable[[], Optional[bool]]]
        self._can_probe_regions = False

        self._ema_alpha = 0.04
        self._last_elapsed_for_stats = None

        self._switch_to_spot_laxity_threshold = None
        self._wait_extra_margin = None

        return self

    def _ensure_state(self) -> None:
        if self._num_regions is not None:
            return

        env = self.env
        try:
            self._num_regions = int(env.get_num_regions())
        except Exception:
            self._num_regions = 1

        n = self._num_regions
        self._ema = [0.55] * n
        self._streak_avail = [0] * n
        self._streak_unavail = [0] * n

        gap = float(getattr(env, "gap_seconds", 3600.0))
        o = float(getattr(self, "restart_overhead", 0.0))

        self._switch_to_spot_laxity_threshold = max(2.0 * 3600.0, 2.0 * gap, 10.0 * o)
        self._wait_extra_margin = max(0.5 * gap, 5.0 * o, 120.0)

        self._spot_reader = self._build_spot_reader()
        self._can_probe_regions = (self._spot_reader is not None) and (n > 1)

    def _build_spot_reader(self) -> Optional[Callable[[], Optional[bool]]]:
        env = self.env
        candidates: List[str] = [
            "has_spot",
            "spot_available",
            "current_has_spot",
            "get_has_spot",
            "get_spot_availability",
            "get_current_has_spot",
            "spot",
            "get_spot",
        ]

        for name in candidates:
            if not hasattr(env, name):
                continue
            attr = getattr(env, name)

            def _reader(a: Any = attr) -> Optional[bool]:
                try:
                    v = a() if callable(a) else a
                except Exception:
                    return None
                return v if isinstance(v, bool) else None

            try:
                test_v = _reader()
            except Exception:
                test_v = None
            if isinstance(test_v, bool):
                return _reader

        return None

    def _read_spot_env(self) -> Optional[bool]:
        if self._spot_reader is None:
            return None
        try:
            return self._spot_reader()
        except Exception:
            return None

    def _update_done_accum(self) -> float:
        tdt = self.task_done_time
        l = len(tdt)
        i = self._last_done_len
        acc = self._done_accum
        while i < l:
            acc += float(tdt[i])
            i += 1
        self._last_done_len = i
        self._done_accum = acc
        return acc

    def _update_region_stats(self, region: int, avail: bool) -> None:
        alpha = self._ema_alpha
        ema = self._ema[region]
        x = 1.0 if avail else 0.0
        self._ema[region] = (1.0 - alpha) * ema + alpha * x

        if avail:
            self._streak_avail[region] += 1
            self._streak_unavail[region] = 0
        else:
            self._streak_unavail[region] += 1
            self._streak_avail[region] = 0

    def _scan_and_choose_spot_region(self, original_region: int) -> int:
        env = self.env
        n = self._num_regions
        reader = self._spot_reader

        best_region = -1
        best_score = -1e18

        current_region = original_region
        if env.get_current_region() != original_region:
            try:
                env.switch_region(original_region)
            except Exception:
                pass

        for r in range(n):
            if r != current_region:
                try:
                    env.switch_region(r)
                except Exception:
                    continue
                current_region = r

            avail = None
            if reader is not None:
                try:
                    avail = reader()
                except Exception:
                    avail = None
            if not isinstance(avail, bool):
                try:
                    env.switch_region(original_region)
                except Exception:
                    pass
                return -2  # cannot scan

            self._update_region_stats(r, avail)
            if not avail:
                continue

            score = 2.0 * self._ema[r] + 0.02 * float(self._streak_avail[r]) - 0.01 * float(self._streak_unavail[r])
            if r == original_region:
                score += 0.12
            if score > best_score:
                best_score = score
                best_region = r

        if best_region >= 0 and best_region != current_region:
            try:
                env.switch_region(best_region)
            except Exception:
                pass
        elif best_region < 0 and current_region != original_region:
            try:
                env.switch_region(original_region)
            except Exception:
                pass

        return best_region

    def _can_wait_one_step(self, work_left: float, time_left: float, gap: float) -> bool:
        if time_left <= gap:
            return False
        time_left_after = time_left - gap
        required = work_left + float(getattr(self, "restart_overhead", 0.0)) + float(self._wait_extra_margin)
        return time_left_after >= required

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_state()

        env = self.env
        gap = float(getattr(env, "gap_seconds", 3600.0))
        elapsed = float(getattr(env, "elapsed_seconds", 0.0))

        done = self._update_done_accum()
        work_left = float(getattr(self, "task_duration", 0.0)) - done
        if work_left <= 0.0:
            return CT_NONE

        deadline = float(getattr(self, "deadline", 0.0))
        time_left = deadline - elapsed

        if time_left <= 0.0:
            return CT_ON_DEMAND

        original_region = 0
        try:
            original_region = int(env.get_current_region())
        except Exception:
            original_region = 0

        spot_env = self._read_spot_env()
        spot_current = spot_env if isinstance(spot_env, bool) else bool(has_spot)

        if self._last_elapsed_for_stats != elapsed:
            if 0 <= original_region < self._num_regions:
                self._update_region_stats(original_region, spot_current)
            self._last_elapsed_for_stats = elapsed

        laxity = time_left - work_left

        keep_ondemand_prefer = (last_cluster_type == CT_ON_DEMAND) and (laxity < float(self._switch_to_spot_laxity_threshold))

        if keep_ondemand_prefer:
            return CT_ON_DEMAND

        if spot_current:
            if last_cluster_type == CT_ON_DEMAND and laxity < float(self._switch_to_spot_laxity_threshold):
                return CT_ON_DEMAND
            return CT_SPOT

        chosen_spot_region = -1
        if self._can_probe_regions:
            chosen_spot_region = self._scan_and_choose_spot_region(original_region)
            if chosen_spot_region == -2:
                chosen_spot_region = -1

        if chosen_spot_region >= 0:
            if last_cluster_type == CT_ON_DEMAND and laxity < float(self._switch_to_spot_laxity_threshold):
                if chosen_spot_region != original_region:
                    try:
                        env.switch_region(original_region)
                    except Exception:
                        pass
                return CT_ON_DEMAND

            spot_now = self._read_spot_env()
            if isinstance(spot_now, bool) and not spot_now:
                try:
                    env.switch_region(original_region)
                except Exception:
                    pass
                chosen_spot_region = -1
            else:
                if not isinstance(spot_now, bool) and not has_spot:
                    try:
                        env.switch_region(original_region)
                    except Exception:
                        pass
                    chosen_spot_region = -1
                else:
                    return CT_SPOT

        if last_cluster_type == CT_ON_DEMAND:
            try:
                env.switch_region(original_region)
            except Exception:
                pass
            return CT_ON_DEMAND

        if self._can_wait_one_step(work_left, time_left, gap):
            try:
                env.switch_region(original_region)
            except Exception:
                pass
            return CT_NONE

        try:
            env.switch_region(original_region)
        except Exception:
            pass
        return CT_ON_DEMAND