import json
import math
from argparse import Namespace
from typing import Callable, List, Optional, Tuple

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_multi_region_v1"

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
        return self

    def _ensure_initialized(self) -> None:
        if getattr(self, "_initialized", False):
            return

        self._initialized = True
        self._done_work_seconds = 0.0
        self._last_task_done_len = 0

        self._force_on_demand = False
        self._consecutive_wait_steps = 0
        self._consecutive_no_spot_steps = 0
        self._od_steps = 0
        self._last_returned: Optional[ClusterType] = None

        self._num_regions = int(self.env.get_num_regions())
        self._spot_streaks = [0] * self._num_regions
        self._spot_seen_steps = [0] * self._num_regions
        self._last_step_index = -1

        self._spot_query_fn: Optional[Callable[[int], bool]] = None
        self._spot_query_supported = False
        self._setup_spot_query()

        self._CT_SPOT = getattr(ClusterType, "SPOT")
        self._CT_OD = getattr(ClusterType, "ON_DEMAND", getattr(ClusterType, "ONDEMAND", None))
        ct_none = getattr(ClusterType, "NONE", None)
        if ct_none is None:
            for v in ClusterType:
                if str(v.name).upper() == "NONE":
                    ct_none = v
                    break
        self._CT_NONE = ct_none if ct_none is not None else list(ClusterType)[0]

    def _setup_spot_query(self) -> None:
        env = self.env

        def _try_bind_method(name: str) -> Optional[Callable[[int], bool]]:
            if not hasattr(env, name):
                return None
            m = getattr(env, name)
            if not callable(m):
                return None

            # Create a fast wrapper with the right arity, decided once.
            cur_region = int(env.get_current_region())
            t_idx = self._get_step_index()
            elapsed = float(getattr(env, "elapsed_seconds", 0.0))

            # Try (region)
            try:
                _ = m(cur_region)
                return lambda r: bool(m(int(r)))
            except TypeError:
                pass
            except Exception:
                return None

            # Try (region, step_index)
            try:
                _ = m(cur_region, t_idx)
                return lambda r: bool(m(int(r), self._get_step_index()))
            except TypeError:
                pass
            except Exception:
                return None

            # Try (region, elapsed_seconds)
            try:
                _ = m(cur_region, elapsed)
                return lambda r: bool(m(int(r), float(getattr(env, "elapsed_seconds", 0.0))))
            except TypeError:
                pass
            except Exception:
                return None

            return None

        for name in (
            "get_has_spot",
            "has_spot",
            "get_spot_availability",
            "get_spot_available",
            "is_spot_available",
            "get_spot",
            "_get_has_spot",
        ):
            fn = _try_bind_method(name)
            if fn is not None:
                self._spot_query_fn = fn
                self._spot_query_supported = True
                return

        # Try trace-like attributes (2D: region x time)
        for attr in (
            "spot_traces",
            "spot_trace",
            "traces",
            "_traces",
            "availability_traces",
            "spot_availabilities",
            "_spot_traces",
        ):
            if not hasattr(env, attr):
                continue
            traces = getattr(env, attr)
            try:
                if traces is None:
                    continue
                if not hasattr(traces, "__len__"):
                    continue
                if len(traces) != int(env.get_num_regions()):
                    continue

                def _trace_query(r: int) -> bool:
                    rr = int(r)
                    t = self._get_step_index()
                    tr = traces[rr]
                    try:
                        n = len(tr)
                        if n <= 0:
                            return False
                        if t < 0:
                            t0 = 0
                        elif t >= n:
                            t0 = n - 1
                        else:
                            t0 = t
                        return bool(tr[t0])
                    except Exception:
                        try:
                            return bool(tr[t])
                        except Exception:
                            return False

                # Smoke test
                _ = _trace_query(int(env.get_current_region()))
                self._spot_query_fn = _trace_query
                self._spot_query_supported = True
                return
            except Exception:
                continue

        self._spot_query_fn = None
        self._spot_query_supported = False

    def _get_step_index(self) -> int:
        g = float(getattr(self.env, "gap_seconds", 1.0)) or 1.0
        e = float(getattr(self.env, "elapsed_seconds", 0.0))
        return int(e // g)

    def _update_done_work(self) -> None:
        td = self.task_done_time
        n = len(td)
        i = self._last_task_done_len
        if i < n:
            s = 0.0
            # Accumulate only new segments
            for j in range(i, n):
                s += float(td[j])
            self._done_work_seconds += s
            self._last_task_done_len = n

    def _refresh_spot_streaks(self, current_has_spot: bool) -> Optional[List[bool]]:
        step_idx = self._get_step_index()
        if step_idx == self._last_step_index:
            return None
        self._last_step_index = step_idx

        n = self._num_regions
        if not self._spot_query_supported or self._spot_query_fn is None:
            # Only update current region streak from provided signal.
            r = int(self.env.get_current_region())
            if current_has_spot:
                self._spot_streaks[r] += 1
            else:
                self._spot_streaks[r] = 0
            self._spot_seen_steps[r] += 1
            return None

        avail = [False] * n
        fn = self._spot_query_fn
        for r in range(n):
            try:
                a = bool(fn(r))
            except Exception:
                a = False
            avail[r] = a
            if a:
                self._spot_streaks[r] += 1
            else:
                self._spot_streaks[r] = 0
            self._spot_seen_steps[r] += 1
        return avail

    def _pick_best_spot_region(self, avail: Optional[List[bool]], current_region: int) -> int:
        if avail is None:
            return current_region
        best_r = -1
        best_streak = -1
        # Prefer current region on ties to reduce switching
        for r, a in enumerate(avail):
            if not a:
                continue
            st = self._spot_streaks[r]
            if st > best_streak:
                best_streak = st
                best_r = r
            elif st == best_streak and r == current_region:
                best_r = r
        return current_region if best_r < 0 else best_r

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_initialized()
        self._update_done_work()

        g = float(getattr(self.env, "gap_seconds", 1.0)) or 1.0
        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0))
        remaining_time = float(self.deadline) - elapsed
        remaining_work = float(self.task_duration) - float(self._done_work_seconds)

        if remaining_work <= 0.0:
            self._consecutive_wait_steps = 0
            self._consecutive_no_spot_steps = 0
            self._od_steps = 0
            self._last_returned = self._CT_NONE
            return self._CT_NONE

        if remaining_time <= 0.0:
            self._last_returned = self._CT_NONE
            return self._CT_NONE

        avail = self._refresh_spot_streaks(has_spot)
        current_region = int(self.env.get_current_region())

        # If slack is too small, commit to on-demand to guarantee completion.
        # Buffer includes one gap and one restart overhead.
        buffer_time = float(self.restart_overhead) + g
        if remaining_time <= remaining_work + buffer_time:
            self._force_on_demand = True

        if self._force_on_demand:
            self._consecutive_wait_steps = 0
            self._consecutive_no_spot_steps = 0
            self._od_steps += 1
            self._last_returned = self._CT_OD
            return self._CT_OD

        # Avoid waiting if we are still paying restart overhead; keep running.
        if float(getattr(self, "remaining_restart_overhead", 0.0)) > 0.0:
            if has_spot:
                self._consecutive_wait_steps = 0
                self._consecutive_no_spot_steps = 0
                self._od_steps = 0
                self._last_returned = self._CT_SPOT
                return self._CT_SPOT
            self._consecutive_wait_steps = 0
            self._consecutive_no_spot_steps += 1
            self._od_steps += 1
            self._last_returned = self._CT_OD
            return self._CT_OD

        # Compute slack and switching hysteresis based on overhead/step ratio.
        slack = remaining_time - remaining_work
        switch_penalty_steps = max(1, int(math.ceil(float(self.restart_overhead) / g)))
        streak_threshold = 1 if switch_penalty_steps <= 2 else min(max(2, switch_penalty_steps // 4), 300)

        # If spot exists somewhere, try to run spot while avoiding thrashing.
        if avail is None:
            any_spot = bool(has_spot)
            best_region = current_region
        else:
            any_spot = any(avail)
            best_region = self._pick_best_spot_region(avail, current_region)

        if any_spot:
            # If we can run spot in some region, decide whether to switch.
            # Prefer staying on spot if already on it and it's available.
            if last_cluster_type == self._CT_SPOT and has_spot:
                self._consecutive_wait_steps = 0
                self._consecutive_no_spot_steps = 0
                self._od_steps = 0
                self._last_returned = self._CT_SPOT
                return self._CT_SPOT

            # If current region doesn't have spot, move to best spot region and use spot.
            if not has_spot:
                self._consecutive_no_spot_steps += 1
                if best_region != current_region and (avail is not None and avail[best_region]):
                    self.env.switch_region(best_region)
                    current_region = best_region
                # Must ensure spot is available in the chosen region; otherwise fall back.
                if avail is not None and avail[current_region]:
                    self._consecutive_wait_steps = 0
                    self._od_steps = 0
                    self._last_returned = self._CT_SPOT
                    return self._CT_SPOT
                # Fallback when we can't confirm.
                if slack > 2.0 * g + float(self.restart_overhead):
                    self._consecutive_wait_steps += 1
                    self._od_steps = 0
                    self._last_returned = self._CT_NONE
                    return self._CT_NONE
                self._consecutive_wait_steps = 0
                self._od_steps += 1
                self._last_returned = self._CT_OD
                return self._CT_OD

            # has_spot is True in current region here.
            # If we are on-demand, only switch back to spot after spot has been stable enough.
            if last_cluster_type == self._CT_OD:
                if self._spot_streaks[current_region] >= streak_threshold and slack > float(self.restart_overhead) + g:
                    self._consecutive_wait_steps = 0
                    self._consecutive_no_spot_steps = 0
                    self._od_steps = 0
                    self._last_returned = self._CT_SPOT
                    return self._CT_SPOT
                # Consider switching to a more stable region if it has a stronger streak.
                if (
                    avail is not None
                    and best_region != current_region
                    and avail[best_region]
                    and self._spot_streaks[best_region] >= streak_threshold
                    and self._spot_streaks[best_region] > self._spot_streaks[current_region] + streak_threshold
                    and slack > float(self.restart_overhead) + g
                ):
                    self.env.switch_region(best_region)
                    self._consecutive_wait_steps = 0
                    self._consecutive_no_spot_steps = 0
                    self._od_steps = 0
                    self._last_returned = self._CT_SPOT
                    return self._CT_SPOT

                self._consecutive_wait_steps = 0
                self._consecutive_no_spot_steps = 0
                self._od_steps += 1
                self._last_returned = self._CT_OD
                return self._CT_OD

            # If we were NONE or other, use spot.
            self._consecutive_wait_steps = 0
            self._consecutive_no_spot_steps = 0
            self._od_steps = 0
            self._last_returned = self._CT_SPOT
            return self._CT_SPOT

        # No spot available (globally, if we can query; otherwise locally).
        self._consecutive_no_spot_steps += 1

        # If slack is sufficiently large, wait a little to avoid on-demand cost.
        # Cap waiting to avoid long stalls.
        max_wait_steps = 6 if switch_penalty_steps <= 6 else min(30, max(6, switch_penalty_steps // 2))
        wait_ok = slack > (3.0 * g + float(self.restart_overhead)) and self._consecutive_wait_steps < max_wait_steps

        if wait_ok:
            self._consecutive_wait_steps += 1
            self._od_steps = 0
            self._last_returned = self._CT_NONE
            return self._CT_NONE

        self._consecutive_wait_steps = 0
        self._od_steps += 1
        self._last_returned = self._CT_OD
        return self._CT_OD
