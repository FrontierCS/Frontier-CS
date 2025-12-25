import json
import os
import math
import gzip
from argparse import Namespace
from array import array
from typing import Any, List, Optional, Tuple

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


def _open_text(path: str):
    if path.endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8", errors="ignore")
    return open(path, "rt", encoding="utf-8", errors="ignore")


def _try_parse_bool_token(tok: str) -> Optional[int]:
    t = tok.strip().strip('"').strip("'")
    if not t:
        return None
    tl = t.lower()
    if tl == "true":
        return 1
    if tl == "false":
        return 0
    if t == "0":
        return 0
    if t == "1":
        return 1
    return None


def _is_number(s: str) -> bool:
    try:
        float(s)
        return True
    except Exception:
        return False


def _load_trace_values(path: str) -> Tuple[List[int], Optional[float]]:
    """
    Returns:
      values: list of 0/1
      dt_seconds: inferred resolution if timestamps exist or can be inferred, else None
    """
    values: List[int] = []
    timestamps: List[float] = []
    try:
        with _open_text(path) as f:
            head = f.read(4096)
            f.seek(0)
            h = head.lstrip()
            if h.startswith("[") or h.startswith("{"):
                data = json.load(f)
                if isinstance(data, dict):
                    # Try common keys
                    for k in ("trace", "availability", "availabilities", "spot", "spots", "values"):
                        if k in data:
                            data = data[k]
                            break
                if isinstance(data, list):
                    if not data:
                        return [], None
                    first = data[0]
                    if isinstance(first, (bool, int, float, str)):
                        for x in data:
                            if isinstance(x, bool):
                                values.append(1 if x else 0)
                            elif isinstance(x, (int, float)):
                                values.append(1 if float(x) > 0 else 0)
                            elif isinstance(x, str):
                                b = _try_parse_bool_token(x)
                                if b is None:
                                    if _is_number(x):
                                        values.append(1 if float(x) > 0 else 0)
                                else:
                                    values.append(b)
                        return values, None
                    if isinstance(first, (list, tuple)) and len(first) >= 2:
                        for item in data:
                            if not isinstance(item, (list, tuple)) or len(item) < 2:
                                continue
                            t = item[0]
                            v = item[1]
                            try:
                                ts = float(t)
                            except Exception:
                                continue
                            timestamps.append(ts)
                            if isinstance(v, bool):
                                values.append(1 if v else 0)
                            elif isinstance(v, (int, float)):
                                values.append(1 if float(v) > 0 else 0)
                            elif isinstance(v, str):
                                b = _try_parse_bool_token(v)
                                if b is None:
                                    if _is_number(v):
                                        values.append(1 if float(v) > 0 else 0)
                                    else:
                                        continue
                                else:
                                    values.append(b)
                        dt = None
                        if len(timestamps) >= 2:
                            diffs = []
                            last = timestamps[0]
                            for ts in timestamps[1:]:
                                d = ts - last
                                if d > 0:
                                    diffs.append(d)
                                last = ts
                            if diffs:
                                diffs.sort()
                                dt = diffs[len(diffs) // 2]
                                if dt <= 0:
                                    dt = None
                        return values, dt
                    if isinstance(first, dict):
                        # Try to locate timestamp and availability keys
                        tkeys = ("t", "time", "timestamp", "ts")
                        vkeys = ("has_spot", "spot", "available", "availability", "avail")
                        for item in data:
                            if not isinstance(item, dict):
                                continue
                            ts = None
                            for tk in tkeys:
                                if tk in item and _is_number(str(item[tk])):
                                    ts = float(item[tk])
                                    break
                            vv = None
                            for vk in vkeys:
                                if vk in item:
                                    vv = item[vk]
                                    break
                            if vv is None:
                                continue
                            if ts is not None:
                                timestamps.append(ts)
                            if isinstance(vv, bool):
                                values.append(1 if vv else 0)
                            elif isinstance(vv, (int, float)):
                                values.append(1 if float(vv) > 0 else 0)
                            elif isinstance(vv, str):
                                b = _try_parse_bool_token(vv)
                                if b is None:
                                    if _is_number(vv):
                                        values.append(1 if float(vv) > 0 else 0)
                                    else:
                                        continue
                                else:
                                    values.append(b)
                        dt = None
                        if len(timestamps) >= 2:
                            diffs = []
                            last = timestamps[0]
                            for ts in timestamps[1:]:
                                d = ts - last
                                if d > 0:
                                    diffs.append(d)
                                last = ts
                            if diffs:
                                diffs.sort()
                                dt = diffs[len(diffs) // 2]
                                if dt <= 0:
                                    dt = None
                        return values, dt
                return [], None

            # Text/CSV style
            first_ts = None
            prev_ts = None
            diffs = []
            for line in f:
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                if "," in s:
                    parts = [p.strip() for p in s.split(",")]
                else:
                    parts = s.split()
                if not parts:
                    continue

                # Skip header-like lines
                if not _is_number(parts[0]) and all(_try_parse_bool_token(p) is None and not (p == "0" or p == "1") for p in parts):
                    continue

                ts_val = None
                if _is_number(parts[0]):
                    try:
                        ts_val = float(parts[0])
                    except Exception:
                        ts_val = None

                v = None
                for tok in reversed(parts):
                    b = _try_parse_bool_token(tok)
                    if b is not None:
                        v = b
                        break
                if v is None:
                    # Try find any explicit 0/1 token
                    for tok in parts:
                        if tok == "0":
                            v = 0
                            break
                        if tok == "1":
                            v = 1
                            break
                if v is None:
                    continue

                values.append(v)
                if ts_val is not None:
                    timestamps.append(ts_val)
                    if first_ts is None:
                        first_ts = ts_val
                    if prev_ts is not None:
                        d = ts_val - prev_ts
                        if d > 0:
                            diffs.append(d)
                    prev_ts = ts_val

            dt = None
            if diffs:
                diffs.sort()
                dt = diffs[len(diffs) // 2]
                if dt <= 0:
                    dt = None
            return values, dt
    except Exception:
        return [], None


def _infer_dt(values_len: int, horizon_seconds: float, gap_seconds: float) -> float:
    if values_len <= 0:
        return gap_seconds
    # Prefer to treat as already at gap resolution if long enough
    horizon_steps = int(math.ceil(horizon_seconds / gap_seconds)) if gap_seconds > 0 else values_len
    if values_len >= horizon_steps:
        return gap_seconds
    dt_guess = horizon_seconds / float(values_len)
    candidates = [1, 2, 5, 10, 15, 30, 60, 120, 300, 600, 900, 1800, 3600]
    best = gap_seconds
    best_err = float("inf")
    for c in candidates:
        err = abs(c - dt_guess)
        if err < best_err:
            best_err = err
            best = float(c)
    # If extremely off, fall back to gap
    if best_err > max(5.0, 0.2 * dt_guess):
        return gap_seconds
    return best


def _resample_to_steps(values: List[int], dt_seconds: float, horizon_steps: int, gap_seconds: float) -> bytearray:
    if horizon_steps <= 0:
        return bytearray()
    if not values:
        return bytearray(b"\x00" * horizon_steps)

    dt = dt_seconds if dt_seconds and dt_seconds > 0 else gap_seconds
    if dt <= 0:
        dt = 1.0

    out = bytearray(horizon_steps)
    n = len(values)

    if dt <= gap_seconds and gap_seconds % dt == 0:
        m = int(round(gap_seconds / dt))
        if m <= 1:
            # same or finer but effectively 1:1
            for k in range(horizon_steps):
                si = int((k * gap_seconds) // dt)
                out[k] = 1 if (0 <= si < n and values[si]) else 0
            return out
        # Conservative: require all subpoints in the gap to be available
        si = 0
        for k in range(horizon_steps):
            if si >= n:
                out[k] = 0
            else:
                end = si + m
                if end > n:
                    end = n
                ok = 1
                for j in range(si, end):
                    if values[j] == 0:
                        ok = 0
                        break
                out[k] = ok
            si += m
        return out

    # Generic mapping using floor at step start
    for k in range(horizon_steps):
        si = int((k * gap_seconds) // dt)
        out[k] = 1 if (0 <= si < n and values[si]) else 0
    return out


class Solution(MultiRegionStrategy):
    NAME = "deadline_spot_greedy_v1"

    def solve(self, spec_path: str) -> "Solution":
        with open(spec_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)

        self._spec_path = spec_path
        self._spec_dir = os.path.dirname(os.path.abspath(spec_path))
        self._trace_files = list(config.get("trace_files", []))
        self._prepared = False

        self._done_sum = 0.0
        self._prev_done_len = 0

        # Precomputed placeholders
        self._gap = None
        self._T = 0
        self._R = 0
        self._avail = None
        self._run_len = None
        self._best_region = None
        self._best_run_steps = None
        self._any_spot = None
        self._schedule_region = None
        self._spot_steps_suffix = None
        self._no_spot_steps_suffix = None
        self._restart_suffix = None

        self._task_duration_sec = None
        self._deadline_sec = None
        self._restart_overhead_sec = None

        self._hard_margin_sec = None
        self._start_spot_threshold_sec = None
        self._switch_to_spot_threshold_sec = None
        return self

    def _ensure_prepared(self) -> None:
        if self._prepared:
            return
        try:
            gap = float(getattr(self.env, "gap_seconds", 1.0))
            if not (gap > 0):
                gap = 1.0
            self._gap = gap

            # Normalize base attributes (seconds)
            td = self.task_duration[0] if isinstance(self.task_duration, (list, tuple)) else self.task_duration
            dl = self.deadline[0] if isinstance(self.deadline, (list, tuple)) else self.deadline
            ro = self.restart_overhead[0] if isinstance(self.restart_overhead, (list, tuple)) else self.restart_overhead
            self._task_duration_sec = float(td)
            self._deadline_sec = float(dl)
            self._restart_overhead_sec = float(ro)

            horizon_steps = int(math.ceil(self._deadline_sec / gap))
            if horizon_steps <= 0:
                horizon_steps = 1
            self._T = horizon_steps

            # Region count
            num_regions_env = int(self.env.get_num_regions())
            trace_files = []
            for p in self._trace_files:
                if not isinstance(p, str):
                    continue
                if not os.path.isabs(p):
                    p2 = os.path.join(self._spec_dir, p)
                else:
                    p2 = p
                trace_files.append(p2)

            self._R = min(num_regions_env, len(trace_files)) if trace_files else num_regions_env
            if self._R <= 0:
                self._R = num_regions_env

            avail: List[bytearray] = []
            run_len: List[array] = []
            best_region = array("h", [-1]) * self._T
            best_run_steps = array("I", [0]) * self._T

            # Load traces if provided
            if trace_files and self._R > 0:
                for r in range(self._R):
                    path = trace_files[r]
                    vals, dt = _load_trace_values(path)
                    if dt is None:
                        dt = _infer_dt(len(vals), self._deadline_sec, gap)
                    a = _resample_to_steps(vals, float(dt), self._T, gap)
                    avail.append(a)

                # Compute run lengths
                for r in range(self._R):
                    rl = array("I", [0]) * (self._T + 1)
                    a = avail[r]
                    for t in range(self._T - 1, -1, -1):
                        if a[t]:
                            rl[t] = rl[t + 1] + 1
                        else:
                            rl[t] = 0
                    run_len.append(rl)

                # Compute best region per step
                for t in range(self._T):
                    br = -1
                    brl = 0
                    for r in range(self._R):
                        if avail[r][t]:
                            rl = run_len[r][t]
                            if rl > brl:
                                brl = rl
                                br = r
                    best_region[t] = br
                    best_run_steps[t] = brl

                # Minimal-switch schedule to cover spot whenever possible
                schedule_region = array("h", [-1]) * self._T
                cur = -1
                for t in range(self._T):
                    if cur != -1 and avail[cur][t]:
                        schedule_region[t] = cur
                    else:
                        cur = int(best_region[t])
                        schedule_region[t] = cur

                any_spot = bytearray(self._T)
                for t in range(self._T):
                    any_spot[t] = 1 if schedule_region[t] != -1 else 0

                # Suffix counts for forecasts
                spot_steps_suffix = array("I", [0]) * (self._T + 1)
                no_spot_steps_suffix = array("I", [0]) * (self._T + 1)
                restart_suffix = array("I", [0]) * (self._T + 1)

                prev = -2
                restart_flag = bytearray(self._T)
                for t in range(self._T):
                    sr = int(schedule_region[t])
                    if sr != -1 and (t == 0 or sr != prev):
                        restart_flag[t] = 1
                    else:
                        restart_flag[t] = 0
                    prev = sr

                for t in range(self._T - 1, -1, -1):
                    spot_steps_suffix[t] = spot_steps_suffix[t + 1] + (1 if any_spot[t] else 0)
                    no_spot_steps_suffix[t] = no_spot_steps_suffix[t + 1] + (0 if any_spot[t] else 1)
                    restart_suffix[t] = restart_suffix[t + 1] + (1 if restart_flag[t] else 0)

                self._avail = avail
                self._run_len = run_len
                self._best_region = best_region
                self._best_run_steps = best_run_steps
                self._any_spot = any_spot
                self._schedule_region = schedule_region
                self._spot_steps_suffix = spot_steps_suffix
                self._no_spot_steps_suffix = no_spot_steps_suffix
                self._restart_suffix = restart_suffix
            else:
                self._avail = None

            # Heuristic parameters
            self._hard_margin_sec = max(2.0 * self._restart_overhead_sec + 2.0 * gap, 5.0 * gap)
            self._start_spot_threshold_sec = max(self._restart_overhead_sec + 60.0, 2.0 * gap)
            self._switch_to_spot_threshold_sec = max(2.0 * self._restart_overhead_sec + 60.0, 2.0 * gap)

            self._prepared = True
        except Exception:
            # Fallback: no trace use
            self._avail = None
            self._prepared = True

    def _update_done_sum(self) -> float:
        td = getattr(self, "task_done_time", None)
        if not td:
            return self._done_sum
        n = len(td)
        if n > self._prev_done_len:
            # Usually 0 or 1 append; handle batch just in case
            for i in range(self._prev_done_len, n):
                try:
                    self._done_sum += float(td[i])
                except Exception:
                    pass
            self._prev_done_len = n
        return self._done_sum

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_prepared()

        gap = float(getattr(self.env, "gap_seconds", 1.0) or 1.0)
        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)

        done = self._update_done_sum()
        task_duration = float(self._task_duration_sec if self._task_duration_sec is not None else 0.0)
        deadline = float(self._deadline_sec if self._deadline_sec is not None else 0.0)
        remaining_work = task_duration - done
        if remaining_work <= 0:
            return ClusterType.NONE

        remaining_time = deadline - elapsed
        if remaining_time <= 0:
            return ClusterType.NONE

        idx = int(elapsed // gap) if gap > 0 else 0
        if idx < 0:
            idx = 0
        if self._T and idx >= self._T:
            # Past our horizon; safest is to run on-demand if unfinished
            return ClusterType.ON_DEMAND

        # Safety first: if we are critically behind, always run something
        urgent = remaining_work >= (remaining_time - float(self._hard_margin_sec or 0.0))

        # If no traces loaded, fallback behavior
        if not self._avail or not self._best_region or not self._best_run_steps:
            if has_spot:
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND if urgent else ClusterType.NONE

        # Forecast quantities for no-spot decisions
        spot_steps_future = int(self._spot_steps_suffix[idx]) if self._spot_steps_suffix else 0
        restart_future = int(self._restart_suffix[idx]) if self._restart_suffix else 0
        no_spot_steps_future = int(self._no_spot_steps_suffix[idx]) if self._no_spot_steps_suffix else 0

        future_spot_work = spot_steps_future * gap - restart_future * float(self._restart_overhead_sec or 0.0)
        if future_spot_work < 0.0:
            future_spot_work = 0.0
        on_demand_needed = remaining_work - future_spot_work
        if on_demand_needed < 0.0:
            on_demand_needed = 0.0
        no_spot_future_sec = no_spot_steps_future * gap

        best_r = int(self._best_region[idx]) if self._best_region else -1
        best_run_sec = float(int(self._best_run_steps[idx])) * gap if self._best_run_steps else 0.0
        any_spot_now = best_r != -1 and best_run_sec > 0.0

        # Avoid resetting restart overhead mid-payment unless forced
        try:
            remaining_oh = float(getattr(self, "remaining_restart_overhead", 0.0) or 0.0)
        except Exception:
            remaining_oh = 0.0

        if any_spot_now:
            # Decide whether to use spot vs on-demand vs none
            if urgent:
                want_spot = True
            else:
                if last_cluster_type == ClusterType.ON_DEMAND:
                    if remaining_oh > 0.0:
                        want_spot = False
                    else:
                        want_spot = best_run_sec >= float(self._switch_to_spot_threshold_sec or 0.0)
                elif last_cluster_type == ClusterType.NONE:
                    # If we need on-demand later anyway, grab spot whenever it appears.
                    want_spot = (best_run_sec >= float(self._start_spot_threshold_sec or 0.0)) or (on_demand_needed > 0.0)
                else:
                    # already on spot
                    want_spot = True

            if want_spot:
                cur_r = int(self.env.get_current_region())
                switched = False

                # If already on spot and current region still has spot, do not switch.
                cur_has_spot = False
                if 0 <= cur_r < len(self._avail):
                    cur_has_spot = bool(self._avail[cur_r][idx])

                if last_cluster_type == ClusterType.SPOT and cur_has_spot:
                    target_r = cur_r
                else:
                    target_r = best_r

                if target_r != -1 and target_r != cur_r:
                    try:
                        self.env.switch_region(int(target_r))
                        switched = True
                        cur_r = target_r
                    except Exception:
                        pass

                # Validate spot availability (conservative: if we didn't switch, respect has_spot arg)
                spot_ok = False
                if 0 <= cur_r < len(self._avail):
                    spot_ok = bool(self._avail[cur_r][idx])
                if not switched and not has_spot:
                    spot_ok = False

                if spot_ok:
                    return ClusterType.SPOT

                # If spot isn't actually available, fall back
                return ClusterType.ON_DEMAND if urgent else ClusterType.NONE

            # Not using spot even though available
            if last_cluster_type == ClusterType.ON_DEMAND:
                return ClusterType.ON_DEMAND
            return ClusterType.NONE if not urgent else ClusterType.ON_DEMAND

        # No spot anywhere now
        if urgent:
            return ClusterType.ON_DEMAND

        # Prefer to schedule required on-demand within no-spot windows; if we skip this step,
        # remaining no-spot capacity shrinks by gap.
        must_use_ondemand = on_demand_needed > max(0.0, no_spot_future_sec - gap)

        if must_use_ondemand:
            return ClusterType.ON_DEMAND

        # Otherwise, pause to save cost; if currently on-demand, consider stopping if enough slack
        if last_cluster_type == ClusterType.ON_DEMAND:
            if remaining_work <= (remaining_time - 3.0 * float(self._hard_margin_sec or 0.0)):
                return ClusterType.NONE
            return ClusterType.ON_DEMAND

        return ClusterType.NONE
