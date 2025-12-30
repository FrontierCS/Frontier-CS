import json
import math
import os
import gzip
from argparse import Namespace
from array import array
from typing import Any, List, Optional, Tuple

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


def _cluster_member(name: str) -> ClusterType:
    members = getattr(ClusterType, "__members__", {})
    if name in members:
        return members[name]
    # Fallbacks for potential naming differences
    alt = {
        "NONE": ["None", "NO_CLUSTER", "NULL"],
        "SPOT": ["Spot", "SPOT_INSTANCE"],
        "ON_DEMAND": ["OnDemand", "ONDEMAND", "ON_DEMAND_INSTANCE"],
    }.get(name, [])
    for k in alt:
        if k in members:
            return members[k]
    return getattr(ClusterType, name)


CT_SPOT = _cluster_member("SPOT")
CT_OND = _cluster_member("ON_DEMAND")
CT_NONE = _cluster_member("NONE")


def _open_maybe_gzip(path: str):
    if path.endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8")
    return open(path, "rt", encoding="utf-8")


def _to_bool01(x: Any) -> int:
    if isinstance(x, bool):
        return 1 if x else 0
    if isinstance(x, (int, float)):
        return 1 if x > 0 else 0
    if isinstance(x, str):
        s = x.strip().lower()
        if s in ("1", "true", "t", "yes", "y", "spot", "available", "avail", "up"):
            return 1
        if s in ("0", "false", "f", "no", "n", "none", "unavailable", "down"):
            return 0
        try:
            v = float(s)
            return 1 if v > 0 else 0
        except Exception:
            return 0
    return 0


def _extract_trace_sequence(data: Any) -> Optional[List[int]]:
    # Common formats:
    # 1) [0/1, 0/1, ...]
    # 2) {"availability":[...]} or {"spot":[...]} etc.
    # 3) [{"available":0/1}, ...] or [{"spot":true}, ...]
    if data is None:
        return None
    if isinstance(data, list):
        if not data:
            return []
        first = data[0]
        if isinstance(first, (bool, int, float, str)):
            return [_to_bool01(v) for v in data]
        if isinstance(first, dict):
            # Try common keys per element
            keys = ("has_spot", "spot", "available", "availability", "avail", "up")
            out = []
            for e in data:
                if not isinstance(e, dict):
                    return None
                val = None
                for k in keys:
                    if k in e:
                        val = e[k]
                        break
                if val is None:
                    # try first numeric/bool-like value
                    for v in e.values():
                        if isinstance(v, (bool, int, float, str)):
                            val = v
                            break
                out.append(_to_bool01(val))
            return out
        return None
    if isinstance(data, dict):
        for k in ("availability", "avail", "has_spot", "spot", "trace", "data", "series"):
            if k in data:
                seq = _extract_trace_sequence(data[k])
                if seq is not None:
                    return seq
        # Try any list-like value
        for v in data.values():
            seq = _extract_trace_sequence(v)
            if seq is not None:
                return seq
    return None


def _load_trace_file(path: str) -> Optional[bytearray]:
    try:
        ext = os.path.splitext(path)[1].lower()
        if ext in (".npy", ".npz"):
            try:
                import numpy as np  # type: ignore
            except Exception:
                return None
            if ext == ".npy":
                arr = np.load(path, allow_pickle=False)
                flat = arr.reshape(-1)
                return bytearray(1 if float(x) > 0 else 0 for x in flat.tolist())
            else:
                z = np.load(path, allow_pickle=False)
                if len(z.files) == 0:
                    return None
                arr = z[z.files[0]]
                flat = arr.reshape(-1)
                return bytearray(1 if float(x) > 0 else 0 for x in flat.tolist())

        if ext == ".json" or path.endswith(".json.gz"):
            with _open_maybe_gzip(path) as f:
                data = json.load(f)
            seq = _extract_trace_sequence(data)
            if seq is None:
                return None
            return bytearray(1 if v else 0 for v in seq)

        # Text/csv/tsv: one value per line or comma separated
        vals: List[int] = []
        with _open_maybe_gzip(path) as f:
            for line in f:
                s = line.strip()
                if not s:
                    continue
                # ignore headers
                if any(c.isalpha() for c in s) and not any(ch in s for ch in ("true", "false", "yes", "no")):
                    continue
                parts = s.replace(",", " ").replace("\t", " ").split()
                if not parts:
                    continue
                vals.append(_to_bool01(parts[-1]))
        if not vals:
            return None
        return bytearray(vals)
    except Exception:
        return None


def _compute_runlen(avail: bytearray) -> array:
    n = len(avail)
    run = array("I", [0]) * n
    r = 0
    for i in range(n - 1, -1, -1):
        if avail[i]:
            r += 1
        else:
            r = 0
        run[i] = r
    return run


def _compute_next_true(avail: bytearray) -> array:
    n = len(avail)
    nxt = array("I", [0]) * n
    next_idx = n
    for i in range(n - 1, -1, -1):
        if avail[i]:
            next_idx = i
        nxt[i] = next_idx
    return nxt


class Solution(MultiRegionStrategy):
    NAME = "my_strategy"

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

        self._trace_files: List[str] = list(config.get("trace_files", [])) if isinstance(config, dict) else []
        self._avail: Optional[List[bytearray]] = None
        self._runlen: Optional[List[array]] = None
        self._next_true: Optional[List[array]] = None
        self._any_avail: Optional[bytearray] = None
        self._next_any: Optional[array] = None

        self._trace_valid: bool = False
        self._trace_offset: int = 0

        self._done_sum: float = 0.0
        self._task_done_len: int = 0

        self._overhead_steps: Optional[int] = None
        self._cooldown_steps: Optional[int] = None
        self._last_switch_idx: int = -10**18

        # Best-effort offline trace load (optional; strategy still works without it)
        if self._trace_files:
            avail_list: List[bytearray] = []
            for p in self._trace_files:
                a = _load_trace_file(p)
                if a is None:
                    avail_list = []
                    break
                avail_list.append(a)

            if avail_list:
                self._avail = avail_list
                self._runlen = [_compute_runlen(a) for a in avail_list]
                self._next_true = [_compute_next_true(a) for a in avail_list]

                min_len = min(len(a) for a in avail_list)
                any_av = bytearray(min_len)
                # any_av[t] = OR over regions
                for a in avail_list:
                    mv = memoryview(a)
                    for i in range(min_len):
                        any_av[i] = 1 if (any_av[i] or mv[i]) else 0
                self._any_avail = any_av
                next_any = array("I", [0]) * min_len
                next_idx = min_len
                for i in range(min_len - 1, -1, -1):
                    if any_av[i]:
                        next_idx = i
                    next_any[i] = next_idx
                self._next_any = next_any

                self._trace_valid = True

        return self

    def _update_done_sum(self) -> None:
        td = self.task_done_time
        n = len(td)
        if n > self._task_done_len:
            self._done_sum += sum(td[self._task_done_len : n])
            self._task_done_len = n

    def _get_gap(self) -> float:
        gap = getattr(self.env, "gap_seconds", None)
        if gap is None:
            return 3600.0
        try:
            g = float(gap)
            return g if g > 0 else 3600.0
        except Exception:
            return 3600.0

    def _ensure_cached_steps(self, gap: float) -> None:
        if self._overhead_steps is not None and self._cooldown_steps is not None:
            return
        oh = float(self.restart_overhead) if self.restart_overhead is not None else 0.0
        if gap <= 0:
            self._overhead_steps = 1
            self._cooldown_steps = 1
            return
        # conservative: if overhead spans multiple steps, avoid rapid switching
        overhead_steps = int(math.ceil(oh / gap)) if oh > 0 else 0
        self._overhead_steps = overhead_steps
        self._cooldown_steps = max(1, overhead_steps)

    def _calibrate_trace_index(self, base_idx: int, cur_region: int, has_spot: bool) -> Optional[int]:
        if not self._trace_valid or self._avail is None:
            return None
        if cur_region < 0 or cur_region >= len(self._avail):
            return None

        a = self._avail[cur_region]
        # Try current offset, else search small window
        cand = base_idx + self._trace_offset
        if 0 <= cand < len(a):
            if bool(a[cand]) == bool(has_spot):
                return cand

        best_off = None
        for off in range(-3, 4):
            idx = base_idx + off
            if 0 <= idx < len(a) and bool(a[idx]) == bool(has_spot):
                best_off = off
                break

        if best_off is not None:
            self._trace_offset = best_off
            idx = base_idx + self._trace_offset
            if 0 <= idx < len(a):
                return idx

        self._trace_valid = False
        return None

    def _pick_best_spot_region(self, idx: int, num_regions: int) -> Tuple[int, int]:
        # returns (region, runlen), or (-1, 0) if none
        if not self._trace_valid or self._avail is None or self._runlen is None:
            return -1, 0
        best_r = -1
        best_len = 0
        for r in range(min(num_regions, len(self._avail))):
            a = self._avail[r]
            if idx < 0 or idx >= len(a):
                continue
            if a[idx]:
                rl = self._runlen[r][idx]
                if rl > best_len:
                    best_len = rl
                    best_r = r
        return best_r, best_len

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._update_done_sum()

        remaining_work = float(self.task_duration) - float(self._done_sum)
        if remaining_work <= 0:
            return CT_NONE

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0))
        time_left = float(self.deadline) - elapsed
        if time_left <= 0:
            return CT_OND

        gap = self._get_gap()
        self._ensure_cached_steps(gap)

        pending_oh = float(getattr(self, "remaining_restart_overhead", 0.0) or 0.0)
        required = remaining_work + pending_oh
        slack = time_left - required

        # If restart overhead is in progress, avoid actions that would reset it unless necessary.
        if pending_oh > 1e-9:
            if last_cluster_type == CT_SPOT:
                if has_spot:
                    return CT_SPOT
                return CT_OND
            if last_cluster_type == CT_OND:
                return CT_OND
            return CT_SPOT if has_spot else CT_OND

        # Conservative panic threshold to ensure finishing before deadline.
        # Use on-demand when slack is tight.
        panic_margin = max(2.0 * gap, 3.0 * float(self.restart_overhead))
        if slack <= panic_margin:
            if last_cluster_type == CT_SPOT and has_spot:
                return CT_SPOT
            return CT_OND

        # Trace-based multi-region decision (if traces loaded and aligned).
        idx: Optional[int] = None
        if self._trace_valid and self._avail is not None and self._runlen is not None:
            try:
                cur_region = int(self.env.get_current_region())
                num_regions = int(self.env.get_num_regions())
            except Exception:
                cur_region = 0
                num_regions = len(self._avail)

            base_idx = int(elapsed // gap) if gap > 0 else 0
            idx = self._calibrate_trace_index(base_idx, cur_region, has_spot)

            if idx is not None:
                best_r, best_len = self._pick_best_spot_region(idx, num_regions)
                if best_r != -1:
                    # Decide whether to switch to the best region.
                    overhead_steps = int(self._overhead_steps or 0)
                    cooldown = int(self._cooldown_steps or 1)
                    min_len_switch = max(2, overhead_steps + 2)

                    # Current region predicted state
                    cur_has = False
                    cur_len = 0
                    if 0 <= cur_region < len(self._avail):
                        a_cur = self._avail[cur_region]
                        if idx < len(a_cur) and a_cur[idx]:
                            cur_has = True
                            cur_len = int(self._runlen[cur_region][idx])

                    if cur_region != best_r:
                        # Avoid thrashing
                        if idx - self._last_switch_idx >= cooldown:
                            # Switch if we don't currently have spot, or current run is short
                            should_switch = (not cur_has) or (cur_len < min_len_switch and best_len >= min_len_switch)
                            # Also allow switch if best is much better
                            if (not should_switch) and best_len >= cur_len + max(3, overhead_steps + 1):
                                should_switch = True

                            # Need enough slack to absorb potential switch overhead
                            if should_switch and slack > (float(self.restart_overhead) + gap):
                                try:
                                    self.env.switch_region(best_r)
                                    self._last_switch_idx = idx
                                    cur_region = best_r
                                    cur_has = True
                                except Exception:
                                    pass

                    # If spot predicted in chosen region at this idx, use it.
                    if 0 <= cur_region < len(self._avail):
                        a_new = self._avail[cur_region]
                        if idx < len(a_new) and a_new[idx]:
                            return CT_SPOT
                        # If mismatch after switch, disable traces to avoid errors.
                        if cur_region == best_r:
                            self._trace_valid = False

                # No spot anywhere right now (per traces). Decide NONE vs ON_DEMAND.
                wait_margin = max(2.0 * gap, 4.0 * float(self.restart_overhead))
                if self._any_avail is not None and self._next_any is not None:
                    if 0 <= idx < len(self._any_avail):
                        next_idx = int(self._next_any[idx])
                        if next_idx < len(self._any_avail):
                            wait_steps = next_idx - idx
                            # Wait if we have slack to spare until spot resumes somewhere.
                            if slack > (wait_steps * gap + float(self.restart_overhead) + wait_margin):
                                return CT_NONE
                if slack > wait_margin:
                    return CT_NONE
                return CT_OND

        # Fallback without reliable traces:
        if has_spot:
            return CT_SPOT

        wait_margin = max(2.0 * gap, 4.0 * float(self.restart_overhead))
        if slack > wait_margin:
            return CT_NONE
        return CT_OND