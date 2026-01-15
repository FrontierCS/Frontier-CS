import json
import math
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


_CT_SPOT = ClusterType.SPOT
_CT_OD = ClusterType.ON_DEMAND
_CT_NONE = getattr(ClusterType, "NONE", None)
if _CT_NONE is None:
    _CT_NONE = getattr(ClusterType, "None")


class Solution(MultiRegionStrategy):
    NAME = "cb_late_mr_v1"

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

    def _ensure_state(self):
        if getattr(self, "_state_init", False):
            return

        self._state_init = True
        self._committed_on_demand = False

        self._last_task_done_len = 0
        self._done_so_far = 0.0

        self._steps_since_switch = 10**9
        self._min_steps_between_switches = 1

        self._region_visits = None
        self._region_spot_true = None

        self._spot_query = None
        self._spot_query_checked = False

        self._no_spot_streak = 0

    def _as_scalar(self, x):
        if isinstance(x, (list, tuple)):
            return float(x[0]) if x else 0.0
        return float(x)

    def _update_done_so_far(self):
        td = self.task_done_time
        if not td:
            return
        l = len(td)
        if l > self._last_task_done_len:
            self._done_so_far += sum(td[self._last_task_done_len : l])
            self._last_task_done_len = l

    def _buffer_seconds(self, gap, restart_overhead):
        # Avoid dependence on huge gaps, but still account for discretization when gaps are small.
        # Cap at 15 minutes.
        return max(2.0 * restart_overhead, min(3.0 * gap, 900.0))

    def _overhead_if_choose(self, last_cluster_type, chosen_cluster_type, switching_region=False):
        if chosen_cluster_type == _CT_NONE:
            return 0.0
        if switching_region:
            return self._as_scalar(self.restart_overhead)
        if last_cluster_type != chosen_cluster_type:
            return self._as_scalar(self.restart_overhead)
        return float(getattr(self, "remaining_restart_overhead", 0.0) or 0.0)

    def _maybe_init_region_stats(self):
        if self._region_visits is not None:
            return
        n = int(self.env.get_num_regions())
        self._region_visits = [0] * n
        self._region_spot_true = [0] * n

    def _choose_explore_region(self, cur_region):
        n = len(self._region_visits)
        if n <= 1:
            return None

        # Beta(1,1) prior for unseen regions.
        best_idx = None
        best_score = -1.0
        best_visits = 10**18
        for i in range(n):
            if i == cur_region:
                continue
            v = self._region_visits[i]
            s = self._region_spot_true[i]
            p = (s + 1.0) / (v + 2.0)
            # Prefer higher p; tie-break on fewer visits to explore.
            if p > best_score + 1e-12 or (abs(p - best_score) <= 1e-12 and v < best_visits):
                best_score = p
                best_visits = v
                best_idx = i
        return best_idx

    def _detect_spot_query(self):
        # Best-effort detection of an API to query spot availability per region at current time.
        # If unavailable, multi-region still works via exploration (switching while idle).
        if self._spot_query_checked:
            return
        self._spot_query_checked = True

        env = self.env
        n = int(env.get_num_regions())
        cur = int(env.get_current_region())

        seq_names = (
            "spot_availability",
            "spot_available",
            "has_spot",
            "spot",
            "region_has_spot",
            "region_spot",
        )
        for name in seq_names:
            if not hasattr(env, name):
                continue
            attr = getattr(env, name)
            if isinstance(attr, (list, tuple)) and len(attr) == n:
                try:
                    if isinstance(attr[cur], bool):
                        self._spot_query = lambda idx, _attr=attr: bool(_attr[int(idx)])
                        return
                except Exception:
                    pass
            if isinstance(attr, dict):
                try:
                    v = attr.get(cur, None)
                    if isinstance(v, bool):
                        self._spot_query = lambda idx, _attr=attr: bool(_attr.get(int(idx), False))
                        return
                except Exception:
                    pass

        method_names = (
            "is_spot_available",
            "get_has_spot",
            "get_spot",
            "get_spot_available",
            "get_spot_availability",
            "spot_available_in_region",
            "has_spot_in_region",
        )
        for name in method_names:
            if not hasattr(env, name):
                continue
            m = getattr(env, name)
            if not callable(m):
                continue

            # Try common signatures
            ok = False
            mode = None
            try:
                v = m(cur)
                if isinstance(v, bool):
                    ok = True
                    mode = 1
            except TypeError:
                pass
            except Exception:
                continue

            if not ok:
                try:
                    v = m(cur, env.elapsed_seconds)
                    if isinstance(v, bool):
                        ok = True
                        mode = 2
                except TypeError:
                    pass
                except Exception:
                    continue

            if not ok:
                try:
                    step_idx = int(env.elapsed_seconds / float(getattr(env, "gap_seconds", 1.0) or 1.0))
                    v = m(cur, step_idx)
                    if isinstance(v, bool):
                        ok = True
                        mode = 3
                except TypeError:
                    pass
                except Exception:
                    continue

            if ok:
                if mode == 1:
                    self._spot_query = lambda idx, _m=m: bool(_m(int(idx)))
                elif mode == 2:
                    self._spot_query = lambda idx, _m=m, _env=env: bool(_m(int(idx), _env.elapsed_seconds))
                else:
                    self._spot_query = lambda idx, _m=m, _env=env: bool(
                        _m(int(idx), int(_env.elapsed_seconds / float(getattr(_env, "gap_seconds", 1.0) or 1.0)))
                    )
                return

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_state()

        gap = float(getattr(self.env, "gap_seconds", 1.0) or 1.0)
        restart_overhead = self._as_scalar(self.restart_overhead)
        task_duration = self._as_scalar(self.task_duration)
        deadline = self._as_scalar(self.deadline)

        self._update_done_so_far()
        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        time_left = deadline - elapsed
        remaining = task_duration - self._done_so_far
        if remaining <= 1e-9:
            return _CT_NONE

        cur_region = int(self.env.get_current_region())
        self._maybe_init_region_stats()
        self._region_visits[cur_region] += 1
        if has_spot:
            self._region_spot_true[cur_region] += 1

        if has_spot:
            self._no_spot_streak = 0
        else:
            self._no_spot_streak += 1

        if last_cluster_type == _CT_OD:
            self._committed_on_demand = True
        if self._committed_on_demand:
            return _CT_OD

        buf = self._buffer_seconds(gap, restart_overhead)

        # Time needed if we run a specific cluster continuously from now.
        od_overhead = self._overhead_if_choose(last_cluster_type, _CT_OD, switching_region=False)
        time_needed_od = remaining + od_overhead

        spot_feasible_now = False
        time_needed_spot = float("inf")
        slack_spot = float("-inf")
        if has_spot:
            spot_overhead = self._overhead_if_choose(last_cluster_type, _CT_SPOT, switching_region=False)
            time_needed_spot = remaining + spot_overhead
            spot_feasible_now = time_needed_spot <= time_left + 1e-9
            if spot_feasible_now:
                slack_spot = time_left - time_needed_spot

        od_feasible_now = time_needed_od <= time_left + 1e-9
        slack_od = (time_left - time_needed_od) if od_feasible_now else float("-inf")

        # If spot can comfortably finish (with margin), prefer spot.
        if spot_feasible_now and slack_spot > buf:
            return _CT_SPOT

        # If we're close to the deadline relative to guaranteed completion on OD, commit to OD (if feasible).
        if od_feasible_now and slack_od <= buf:
            self._committed_on_demand = True
            return _CT_OD

        # If OD isn't feasible but spot is, we must use spot.
        if spot_feasible_now and not od_feasible_now:
            return _CT_SPOT

        # If spot is available, and OD is not strictly necessary yet, keep using spot (cheaper).
        if has_spot:
            return _CT_SPOT

        # No spot available: either wait (NONE) or start OD.
        # Safe to idle one step if after losing this gap, we can still finish on OD with restart overhead.
        # Use a conservative assumption: starting OD after idle likely requires a full restart overhead.
        idle_safe = (time_left - gap) >= (remaining + restart_overhead + buf) - 1e-9

        if idle_safe:
            # Explore regions while idle to increase chance of finding spot next step.
            self._detect_spot_query()

            # Avoid switching while an overhead is pending: resetting overhead repeatedly could be harmful
            # for small gaps where overhead spans multiple steps.
            rem_oh = float(getattr(self, "remaining_restart_overhead", 0.0) or 0.0)
            can_switch = rem_oh <= 1e-9 and self._steps_since_switch >= self._min_steps_between_switches

            if can_switch and self.env.get_num_regions() > 1:
                target = None

                # If we can query all regions' spot availability at current time, switch directly to an available one
                # only if we can run spot immediately (but we cannot safely run spot this step without has_spot for new region).
                # Still, we can use the query to choose a region that will likely be spot now and in the next step.
                if self._spot_query is not None:
                    n = int(self.env.get_num_regions())
                    best = None
                    best_score = -1.0
                    for i in range(n):
                        if i == cur_region:
                            continue
                        try:
                            avail = bool(self._spot_query(i))
                        except Exception:
                            avail = False
                        if not avail:
                            continue
                        v = self._region_visits[i]
                        s = self._region_spot_true[i]
                        p = (s + 1.0) / (v + 2.0)
                        if p > best_score:
                            best_score = p
                            best = i
                    target = best if best is not None else self._choose_explore_region(cur_region)
                else:
                    target = self._choose_explore_region(cur_region)

                if target is not None and target != cur_region:
                    try:
                        self.env.switch_region(int(target))
                        self._steps_since_switch = 0
                    except Exception:
                        pass

            self._steps_since_switch += 1
            return _CT_NONE

        # Not safe to idle: start OD and commit.
        self._committed_on_demand = True
        return _CT_OD