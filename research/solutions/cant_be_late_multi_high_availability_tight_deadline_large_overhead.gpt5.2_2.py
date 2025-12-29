import json
import math
import os
import re
from argparse import Namespace
from array import array
from typing import Any, Callable, List, Optional

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

        self._trace_files = list(config.get("trace_files", []))
        self._traces: List[bytearray] = []
        self._runlens: List[array] = []
        self._any_spot: Optional[bytearray] = None
        self._next_any_spot: Optional[array] = None
        self._T: int = 0

        self._done_sum: float = 0.0
        self._done_len: int = 0

        self._initialized: bool = False
        self._gap: float = 0.0

        self._spot_probe_set: bool = False
        self._spot_probe: Optional[Callable[[], bool]] = None

        self._committed_od: bool = False
        self._no_any_spot_streak: int = 0

        # Heuristics (set on first _step when env.gap_seconds is known).
        self._safety_to_od: float = 0.0
        self._wait_slack: float = 0.0

        try:
            self._load_and_precompute_traces(self._trace_files)
        except Exception:
            # If traces fail to load, we still operate using the current-region has_spot signal
            # and on-demand fallback.
            self._traces = []
            self._runlens = []
            self._any_spot = None
            self._next_any_spot = None
            self._T = 0

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        SPOT = getattr(ClusterType, "SPOT")
        ON_DEMAND = getattr(ClusterType, "ON_DEMAND")
        NONE = getattr(ClusterType, "NONE", getattr(ClusterType, "None"))

        if not self._initialized:
            self._gap = float(getattr(self.env, "gap_seconds", 1.0))
            self._safety_to_od = max(2.0 * self._gap, 6.0 * float(self.restart_overhead))
            self._wait_slack = max(3.0 * self._gap, 10.0 * float(self.restart_overhead))
            self._initialized = True

        self._update_done_sum()
        remaining_work = float(self.task_duration) - self._done_sum
        if remaining_work <= 1e-9:
            return NONE

        remaining_time = float(self.deadline) - float(self.env.elapsed_seconds)
        if remaining_time <= 1e-9:
            return ON_DEMAND

        t = int(float(self.env.elapsed_seconds) // self._gap)

        # Initialize spot probe once and validate on current region
        self._ensure_spot_probe(has_spot)

        # Commit to on-demand when close to deadline.
        extra_if_commit_od = float(self.remaining_restart_overhead) if last_cluster_type == ON_DEMAND else float(self.restart_overhead)
        time_needed_od = remaining_work + extra_if_commit_od
        slack_od = remaining_time - time_needed_od
        if slack_od <= self._safety_to_od:
            self._committed_od = True

        if self._committed_od:
            return ON_DEMAND

        curr_spot = bool(has_spot)
        if curr_spot:
            self._no_any_spot_streak = 0
            return SPOT

        # Current region has no spot: attempt to switch to a region with spot.
        best_region = self._select_best_spot_region(t, curr_spot)

        if best_region is not None:
            self._no_any_spot_streak = 0
            return SPOT

        # No spot anywhere (as far as we can tell): decide to wait or use on-demand.
        self._no_any_spot_streak += 1
        wait_steps = self._time_to_next_any_spot_steps(t)
        if wait_steps is not None and wait_steps >= 0:
            wait_time = wait_steps * self._gap
            if (slack_od - wait_time) > self._safety_to_od:
                return NONE
            return ON_DEMAND

        # Without lookahead, only wait briefly if slack is large.
        if slack_od > self._wait_slack and self._no_any_spot_streak <= 2:
            return NONE
        return ON_DEMAND

    def _update_done_sum(self) -> None:
        td = self.task_done_time
        ln = len(td)
        if ln > self._done_len:
            s = 0.0
            for i in range(self._done_len, ln):
                s += float(td[i])
            self._done_sum += s
            self._done_len = ln

    def _ensure_spot_probe(self, has_spot_arg: bool) -> None:
        if self._spot_probe_set:
            return
        self._spot_probe_set = True

        probe = self._discover_spot_probe()
        if probe is None:
            self._spot_probe = None
            return

        try:
            v = bool(probe())
        except Exception:
            self._spot_probe = None
            return

        if v != bool(has_spot_arg):
            self._spot_probe = None
            return

        self._spot_probe = probe

    def _discover_spot_probe(self) -> Optional[Callable[[], bool]]:
        env = self.env
        candidates = (
            ("has_spot", False),
            ("spot_available", False),
            ("spot_availability", False),
            ("is_spot_available", True),
            ("get_has_spot", True),
            ("spot_available_now", True),
        )

        for name, expect_callable in candidates:
            if not hasattr(env, name):
                continue
            attr = getattr(env, name)
            if callable(attr):
                # Prefer zero-arg callable.
                def _mk(m):
                    return lambda: bool(m())
                try:
                    _ = attr()
                    return _mk(attr)
                except TypeError:
                    # Maybe needs region index.
                    try:
                        cur = int(self.env.get_current_region())
                        _ = attr(cur)
                        return (lambda m=attr: bool(m(int(self.env.get_current_region()))))
                    except Exception:
                        continue
                except Exception:
                    continue
            else:
                # Non-callable boolean attribute
                try:
                    _ = bool(attr)
                    return lambda a_name=name: bool(getattr(self.env, a_name))
                except Exception:
                    continue

        return None

    def _trace_spot(self, region: int, t: int) -> bool:
        if not self._traces:
            return False
        if region < 0 or region >= len(self._traces):
            return False
        tr = self._traces[region]
        if t < 0 or t >= len(tr):
            return False
        return bool(tr[t])

    def _time_to_next_any_spot_steps(self, t: int) -> Optional[int]:
        if self._next_any_spot is None or self._any_spot is None:
            return None
        if t < 0:
            return 0
        if t >= self._T:
            return None
        nxt = int(self._next_any_spot[t])
        if nxt >= self._T:
            return None
        return nxt - t

    def _select_best_spot_region(self, t: int, curr_spot: bool) -> Optional[int]:
        num_regions = int(self.env.get_num_regions())
        orig = int(self.env.get_current_region())

        best = None
        best_run = -1

        if self._spot_probe is None and not self._traces:
            return None

        # Scan regions (only when current region lacks spot).
        for r in range(num_regions):
            if r == orig:
                avail = curr_spot
            else:
                self.env.switch_region(r)
                if self._spot_probe is not None:
                    try:
                        avail = bool(self._spot_probe())
                    except Exception:
                        avail = False
                else:
                    avail = self._trace_spot(r, t)

            if avail:
                run = 1
                if self._runlens and 0 <= r < len(self._runlens) and 0 <= t < self._T:
                    run = int(self._runlens[r][t])
                if run > best_run:
                    best_run = run
                    best = r

        if best is None:
            self.env.switch_region(orig)
            return None

        if int(self.env.get_current_region()) != best:
            self.env.switch_region(best)
        return best

    def _load_and_precompute_traces(self, trace_files: List[str]) -> None:
        traces: List[bytearray] = []
        for p in trace_files:
            tr = self._load_trace_file(p)
            traces.append(tr)

        if not traces:
            self._traces = []
            self._runlens = []
            self._any_spot = None
            self._next_any_spot = None
            self._T = 0
            return

        maxlen = max(len(t) for t in traces)
        if maxlen <= 0:
            self._traces = []
            self._runlens = []
            self._any_spot = None
            self._next_any_spot = None
            self._T = 0
            return

        # Pad all to same length with 0 (unavailable).
        for i in range(len(traces)):
            if len(traces[i]) < maxlen:
                traces[i].extend(b"\x00" * (maxlen - len(traces[i])))

        any_spot = bytearray(maxlen)
        for i in range(maxlen):
            v = 0
            for r in range(len(traces)):
                if traces[r][i]:
                    v = 1
                    break
            any_spot[i] = v

        runlens: List[array] = []
        for r in range(len(traces)):
            rl = array("I", [0]) * (maxlen + 1)
            tr = traces[r]
            for i in range(maxlen - 1, -1, -1):
                if tr[i]:
                    rl[i] = rl[i + 1] + 1
                else:
                    rl[i] = 0
            runlens.append(rl)

        next_any = array("I", [0]) * (maxlen + 1)
        nxt = maxlen
        next_any[maxlen] = maxlen
        for i in range(maxlen - 1, -1, -1):
            if any_spot[i]:
                nxt = i
            next_any[i] = nxt

        self._traces = traces
        self._runlens = runlens
        self._any_spot = any_spot
        self._next_any_spot = next_any
        self._T = maxlen

    def _load_trace_file(self, path: str) -> bytearray:
        if not os.path.exists(path):
            return bytearray()

        with open(path, "rb") as f:
            data = f.read()

        if not data:
            return bytearray()

        # Detect json vs text quickly
        i = 0
        n = len(data)
        while i < n and data[i] in b" \t\r\n":
            i += 1
        if i < n and data[i] in (ord("["), ord("{")):
            try:
                obj = json.loads(data.decode("utf-8"))
                vals = self._extract_availability(obj)
                return bytearray(1 if v else 0 for v in vals)
            except Exception:
                pass

        # Parse as text (csv/tsv/space separated)
        text = data.decode("utf-8", errors="ignore")
        out = bytearray()
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = re.split(r"[,\s]+", line)
            v = None
            for tok in reversed(parts):
                if not tok:
                    continue
                try:
                    v = float(tok)
                    break
                except Exception:
                    continue
            if v is None:
                continue
            out.append(1 if v > 0 else 0)
        return out

    def _extract_availability(self, obj: Any) -> List[bool]:
        # Try to find a list-like container holding the trace.
        if isinstance(obj, dict):
            for k in ("availability", "avail", "trace", "data", "values", "spot", "has_spot"):
                if k in obj:
                    return self._extract_availability(obj[k])
            # fallback: pick the first list value
            for v in obj.values():
                if isinstance(v, (list, tuple)):
                    return self._extract_availability(v)
            return []
        if isinstance(obj, (list, tuple)):
            res: List[bool] = []
            for el in obj:
                if isinstance(el, (bool, int, float)):
                    res.append(bool(el))
                elif isinstance(el, dict):
                    vv = None
                    for k in ("available", "availability", "has_spot", "spot", "value", "avail"):
                        if k in el:
                            vv = el[k]
                            break
                    if vv is None:
                        # fallback: any numeric/bool value
                        for vv2 in el.values():
                            if isinstance(vv2, (bool, int, float)):
                                vv = vv2
                                break
                    res.append(bool(vv) if vv is not None else False)
                elif isinstance(el, (list, tuple)) and el:
                    last = el[-1]
                    if isinstance(last, (bool, int, float)):
                        res.append(bool(last))
                    else:
                        try:
                            res.append(float(str(last)) > 0)
                        except Exception:
                            res.append(False)
                else:
                    try:
                        res.append(float(str(el)) > 0)
                    except Exception:
                        res.append(False)
            return res
        return []