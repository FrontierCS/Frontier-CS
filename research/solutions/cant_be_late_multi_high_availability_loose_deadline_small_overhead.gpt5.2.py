import json
import math
import os
from argparse import Namespace
from array import array
from typing import List, Optional, Tuple

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_mr_v1"

    # Prices are fixed in the problem statement; used only for optional heuristics.
    _ON_DEMAND_PRICE = 3.06
    _SPOT_PRICE = 0.9701

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

        self._trace_files = list(config.get("trace_files", [])) if isinstance(config, dict) else []
        self._traces_avail: List[bytearray] = []
        self._traces_streak: List[array] = []
        self._max_trace_len: int = 0

        self._any_avail: Optional[bytearray] = None
        self._next_any: Optional[array] = None

        self._done_sum: float = 0.0
        self._done_len: int = 0

        self._initialized_runtime: bool = False
        self._n_regions_runtime: int = 0

        if self._trace_files:
            for p in self._trace_files:
                avail = self._load_trace_availability(p)
                if avail is None:
                    avail = bytearray()
                self._traces_avail.append(avail)
                self._max_trace_len = max(self._max_trace_len, len(avail))

            for avail in self._traces_avail:
                self._traces_streak.append(self._compute_streak(avail))

            self._recompute_any_next()

        return self

    def _sec_attr(self, x):
        if isinstance(x, (list, tuple)):
            return float(x[0]) if x else 0.0
        return float(x)

    def _update_done_sum(self):
        td = self.task_done_time
        ln = len(td)
        if ln > self._done_len:
            self._done_sum += float(sum(td[self._done_len:ln]))
            self._done_len = ln

    def _idx_now(self) -> int:
        gap = float(self.env.gap_seconds)
        if gap <= 0:
            return 0
        t = float(self.env.elapsed_seconds)
        # Robust floor for float arithmetic
        return int(math.floor((t + 1e-9) / gap))

    def _spot_at(self, region: int, idx: int) -> int:
        if region < 0 or region >= len(self._traces_avail):
            return 0
        av = self._traces_avail[region]
        if idx < 0 or idx >= len(av):
            return 0
        return 1 if av[idx] else 0

    def _streak_at(self, region: int, idx: int) -> int:
        if region < 0 or region >= len(self._traces_streak):
            return 0
        st = self._traces_streak[region]
        if idx < 0 or idx >= len(st):
            return 0
        return int(st[idx])

    def _best_spot_region_now(self, idx: int, n_regions: int) -> Tuple[int, int]:
        # Returns (best_region, best_streak_steps) or (-1, 0) if none have spot.
        best_r = -1
        best_s = 0
        nr = min(n_regions, len(self._traces_avail)) if self._traces_avail else 0
        if nr <= 0:
            return -1, 0
        for r in range(nr):
            s = self._streak_at(r, idx)
            if s > best_s:
                best_s = s
                best_r = r
        if best_s <= 0:
            return -1, 0
        return best_r, best_s

    def _next_any_spot_idx(self, idx: int) -> int:
        if self._next_any is None:
            return 1 << 30
        if idx < 0:
            idx = 0
        if idx >= len(self._next_any):
            return 1 << 30
        return int(self._next_any[idx])

    def _recompute_any_next(self):
        if self._max_trace_len <= 0 or not self._traces_avail:
            self._any_avail = None
            self._next_any = None
            return

        L = self._max_trace_len
        any_av = bytearray(L)

        # OR across regions
        for r, av in enumerate(self._traces_avail):
            m = min(L, len(av))
            for i in range(m):
                if av[i]:
                    any_av[i] = 1

        self._any_avail = any_av
        nxt = array("I", [L + 1]) * (L + 2)
        next_pos = L + 1
        for i in range(L - 1, -1, -1):
            if any_av[i]:
                next_pos = i
            nxt[i] = next_pos
        nxt[L] = next_pos
        nxt[L + 1] = L + 1
        self._next_any = nxt

    def _compute_streak(self, avail: bytearray) -> array:
        L = len(avail)
        st = array("I", [0]) * (L + 1)
        run = 0
        for i in range(L - 1, -1, -1):
            if avail[i]:
                run += 1
            else:
                run = 0
            st[i] = run
        st[L] = 0
        return st

    def _load_trace_availability(self, path: str) -> Optional[bytearray]:
        try:
            if not path or not os.path.exists(path):
                return bytearray()

            # NPY support (optional)
            if path.endswith(".npy"):
                try:
                    import numpy as np  # type: ignore

                    arr = np.load(path, allow_pickle=False)
                    flat = arr.ravel()
                    out = bytearray(int(x) != 0 for x in flat.tolist())
                    return out
                except Exception:
                    pass

            with open(path, "rb") as f:
                head = f.read(4096)
            # JSON support
            s = head.lstrip()
            if s.startswith(b"[") or s.startswith(b"{"):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    vals = []
                    if isinstance(data, list):
                        vals = data
                    elif isinstance(data, dict):
                        for k in ("availability", "available", "has_spot", "spot", "trace", "values"):
                            if k in data and isinstance(data[k], list):
                                vals = data[k]
                                break
                    out = bytearray()
                    for x in vals:
                        if isinstance(x, dict):
                            if "available" in x:
                                out.append(1 if x["available"] else 0)
                            elif "availability" in x:
                                out.append(1 if x["availability"] else 0)
                            elif "has_spot" in x:
                                out.append(1 if x["has_spot"] else 0)
                            elif "interrupt" in x:
                                out.append(0 if x["interrupt"] else 1)
                            elif "interruption" in x:
                                out.append(0 if x["interruption"] else 1)
                            elif "price" in x:
                                v = x["price"]
                                try:
                                    fv = float(v)
                                    out.append(1 if (not math.isnan(fv) and fv > 0.0) else 0)
                                except Exception:
                                    out.append(0)
                            else:
                                out.append(0)
                        else:
                            if isinstance(x, bool):
                                out.append(1 if x else 0)
                            else:
                                try:
                                    fv = float(x)
                                    if math.isnan(fv):
                                        out.append(0)
                                    else:
                                        out.append(1 if fv != 0.0 else 0)
                                except Exception:
                                    out.append(0)
                    return out
                except Exception:
                    pass

            # Text/CSV support
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                first = f.readline()
                if not first:
                    return bytearray()

                delim = "," if "," in first else ("\t" if "\t" in first else None)
                out = bytearray()

                def is_number(tok: str) -> bool:
                    try:
                        float(tok)
                        return True
                    except Exception:
                        return False

                # Header detection
                tokens = [t.strip() for t in (first.strip().split(delim) if delim else first.strip().split()) if t.strip() != ""]
                has_header = any(not is_number(t) for t in tokens)

                col_idx = None
                invert_interrupt = False
                price_like = False

                if has_header and tokens:
                    low = [t.lower() for t in tokens]
                    chosen = None
                    for key in ("availability", "available", "has_spot", "spot"):
                        for j, name in enumerate(low):
                            if key == name or name.endswith(key) or key in name:
                                if "price" in name:
                                    continue
                                chosen = j
                                break
                        if chosen is not None:
                            break
                    if chosen is None:
                        for key in ("interrupt", "interruption", "preempt", "evict"):
                            for j, name in enumerate(low):
                                if key in name:
                                    chosen = j
                                    invert_interrupt = True
                                    break
                            if chosen is not None:
                                break
                    if chosen is None:
                        for j, name in enumerate(low):
                            if "price" in name:
                                chosen = j
                                price_like = True
                                break
                    col_idx = chosen

                    # Read remaining lines after header
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        parts = [p.strip() for p in (line.split(delim) if delim else line.split())]
                        if not parts:
                            continue
                        j = col_idx if col_idx is not None and col_idx < len(parts) else (len(parts) - 1)
                        tok = parts[j]
                        if tok == "" or tok.lower() == "nan":
                            out.append(0 if price_like else 0)
                            continue
                        try:
                            fv = float(tok)
                            if math.isnan(fv):
                                out.append(0)
                            else:
                                if price_like:
                                    out.append(1 if fv > 0.0 else 0)
                                else:
                                    v = 1 if fv != 0.0 else 0
                                    if invert_interrupt:
                                        v = 1 - v
                                    out.append(v)
                        except Exception:
                            tl = tok.lower()
                            if tl in ("true", "t", "yes", "y"):
                                v = 1
                            elif tl in ("false", "f", "no", "n"):
                                v = 0
                            else:
                                v = 0
                            if invert_interrupt:
                                v = 1 - v
                            out.append(v)
                    return out

                # No header: treat each line as numeric; take last column if multiple.
                def parse_line(line: str):
                    line = line.strip()
                    if not line:
                        return None
                    parts = [p.strip() for p in (line.split(delim) if delim else line.split())]
                    if not parts:
                        return None
                    tok = parts[-1]
                    if tok == "" or tok.lower() == "nan":
                        return 0
                    try:
                        fv = float(tok)
                        if math.isnan(fv):
                            return 0
                        return 1 if fv != 0.0 else 0
                    except Exception:
                        tl = tok.lower()
                        if tl in ("true", "t", "yes", "y"):
                            return 1
                        if tl in ("false", "f", "no", "n"):
                            return 0
                        return 0

                v0 = parse_line(first)
                if v0 is not None:
                    out.append(v0)
                for line in f:
                    v = parse_line(line)
                    if v is not None:
                        out.append(v)
                return out
        except Exception:
            return bytearray()

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not self._initialized_runtime:
            try:
                self._n_regions_runtime = int(self.env.get_num_regions())
            except Exception:
                self._n_regions_runtime = 0
            self._initialized_runtime = True

        self._update_done_sum()

        task_duration = self._sec_attr(self.task_duration)
        deadline = self._sec_attr(self.deadline)
        restart_overhead = self._sec_attr(self.restart_overhead)
        t = float(self.env.elapsed_seconds)
        remaining_time = deadline - t
        remaining_work = task_duration - self._done_sum
        if remaining_work <= 1e-9:
            return ClusterType.NONE

        pending_oh = float(getattr(self, "remaining_restart_overhead", 0.0) or 0.0)
        slack = remaining_time - (remaining_work + pending_oh)

        gap = float(self.env.gap_seconds)
        safety = max(0.0, min(0.5 * gap, 4.0 * restart_overhead))

        # If deadline is tight, prefer on-demand to avoid interruption risk and extra restarts.
        if slack <= -safety:
            return ClusterType.ON_DEMAND

        # Avoid wasting already-paid overhead: don't switch cluster type while warmup is pending.
        if pending_oh > 1e-9:
            if last_cluster_type == ClusterType.ON_DEMAND:
                return ClusterType.ON_DEMAND
            if last_cluster_type == ClusterType.SPOT and has_spot:
                return ClusterType.SPOT
            # If spot is unavailable, fall through to choose a feasible action.

        idx = self._idx_now()
        cur_region = 0
        try:
            cur_region = int(self.env.get_current_region())
        except Exception:
            cur_region = 0

        # If no traces loaded, simple fallback.
        if not self._traces_avail:
            if has_spot and slack >= safety:
                return ClusterType.SPOT
            if slack > safety and not has_spot:
                return ClusterType.NONE
            return ClusterType.ON_DEMAND

        n_regions = self._n_regions_runtime if self._n_regions_runtime > 0 else len(self._traces_avail)
        best_r, best_streak = self._best_spot_region_now(idx, n_regions)

        if best_r >= 0 and best_streak > 0:
            # Prefer staying on current spot if already on spot and spot is available here.
            if last_cluster_type == ClusterType.SPOT and has_spot:
                return ClusterType.SPOT

            # If switching/restarting, require some slack to absorb overhead-induced delay.
            if slack < safety:
                return ClusterType.ON_DEMAND

            if best_r != cur_region:
                try:
                    self.env.switch_region(best_r)
                except Exception:
                    pass
            return ClusterType.SPOT

        # No spot anywhere now: wait until next spot if safe; otherwise use on-demand.
        next_idx = self._next_any_spot_idx(idx)
        if next_idx >= (1 << 29):
            # No future spot known; use on-demand unless ample slack to pause.
            if slack > safety:
                return ClusterType.NONE
            return ClusterType.ON_DEMAND

        wait_steps = max(0, next_idx - idx)
        wait_seconds = wait_steps * gap
        if wait_seconds <= slack - safety:
            return ClusterType.NONE
        return ClusterType.ON_DEMAND
