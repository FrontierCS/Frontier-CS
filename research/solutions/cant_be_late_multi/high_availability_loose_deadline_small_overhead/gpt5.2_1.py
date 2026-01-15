import json
import math
import gzip
from argparse import Namespace
from array import array
from typing import List, Optional, Any

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


def _open_maybe_gzip(path: str):
    with open(path, "rb") as f:
        head = f.read(2)
    if head == b"\x1f\x8b":
        return gzip.open(path, "rt", encoding="utf-8", errors="ignore")
    return open(path, "rt", encoding="utf-8", errors="ignore")


def _token_to_num(tok: str) -> Optional[float]:
    t = tok.strip().strip('"').strip("'")
    if not t:
        return None
    low = t.lower()
    if low in ("true", "t", "yes", "y"):
        return 1.0
    if low in ("false", "f", "no", "n"):
        return 0.0
    try:
        return float(t)
    except Exception:
        return None


def _parse_trace_file(path: str) -> List[int]:
    # Returns list of 0/1 values (not yet inverted).
    try:
        with _open_maybe_gzip(path) as f:
            first = f.read(1)
            if not first:
                return []
            rest = f.read()
        content = first + rest
        s = content.lstrip()
        if s.startswith("[") or s.startswith("{"):
            try:
                obj = json.loads(s)
                if isinstance(obj, dict):
                    for k in ("availability", "avail", "spot", "has_spot", "data", "trace"):
                        if k in obj and isinstance(obj[k], list):
                            obj = obj[k]
                            break
                if isinstance(obj, list):
                    out = []
                    for v in obj:
                        if isinstance(v, bool):
                            out.append(1 if v else 0)
                        elif isinstance(v, (int, float)):
                            out.append(1 if float(v) >= 0.5 else 0)
                        elif isinstance(v, str):
                            num = _token_to_num(v)
                            if num is not None:
                                out.append(1 if num >= 0.5 else 0)
                    return out
            except Exception:
                pass
    except Exception:
        pass

    vals: List[int] = []
    try:
        with _open_maybe_gzip(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.replace("\t", ",").replace(" ", ",").split(",")
                num = None
                for tok in reversed(parts):
                    n = _token_to_num(tok)
                    if n is None:
                        continue
                    num = n
                    break
                if num is None:
                    continue
                if abs(num - 0.0) < 1e-9:
                    vals.append(0)
                elif abs(num - 1.0) < 1e-9:
                    vals.append(1)
                else:
                    vals.append(1 if num >= 0.5 else 0)
    except Exception:
        return []
    return vals


class Solution(MultiRegionStrategy):
    NAME = "trace_aware_greedy_v1"

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

        trace_files = config.get("trace_files", [])
        self._trace_files: List[str] = list(trace_files) if isinstance(trace_files, list) else []
        self._raw_traces: List[List[int]] = []
        for p in self._trace_files:
            self._raw_traces.append(_parse_trace_file(p))

        self._prepared = False
        self._n_regions = len(self._raw_traces)
        self._T = 0
        self._avail: List[bytearray] = []
        self._runlen: List[array] = []
        self._any_avail: Optional[bytearray] = None
        self._best_region: Optional[array] = None
        self._next_any: Optional[array] = None

        self._done_len = 0
        self._done_sum = 0.0

        self._switch_penalty_steps = 1
        self._switch_threshold = 1
        self._critical_slack = 0.0
        self._pause_buffer = 0.0
        self._force_ondemand = False
        return self

    def _ensure_prepared(self) -> None:
        if self._prepared:
            return

        gap = float(getattr(self.env, "gap_seconds", 60.0))
        if gap <= 0:
            gap = 60.0

        try:
            n_env = int(self.env.get_num_regions())
        except Exception:
            n_env = self._n_regions if self._n_regions > 0 else len(self._trace_files)

        if n_env <= 0:
            n_env = self._n_regions if self._n_regions > 0 else 1

        if self._n_regions <= 0:
            self._n_regions = n_env
            self._raw_traces = [[] for _ in range(self._n_regions)]
        elif self._n_regions != n_env:
            if self._n_regions > n_env:
                self._raw_traces = self._raw_traces[:n_env]
                self._n_regions = n_env
            else:
                self._raw_traces.extend([[] for _ in range(n_env - self._n_regions)])
                self._n_regions = n_env

        T = int(math.ceil(float(self.deadline) / gap)) + 3
        if T < 8:
            T = 8
        self._T = T

        self._avail = []
        self._runlen = []

        for r in range(self._n_regions):
            raw = self._raw_traces[r] if r < len(self._raw_traces) else []
            L = len(raw)

            if L > 0:
                ones = 0
                for v in raw:
                    ones += 1 if v else 0
                frac_one = ones / max(1, L)
                invert = frac_one < 0.5
                if invert:
                    raw = [0 if v else 1 for v in raw]
            else:
                raw = []

            av = bytearray(T)
            if L <= 0:
                pass
            elif L == T:
                for i, v in enumerate(raw):
                    av[i] = 1 if v else 0
            else:
                for k in range(T):
                    j = int((k * L) / T)
                    if j >= L:
                        j = L - 1
                    av[k] = 1 if raw[j] else 0

            run = array("I", [0]) * T
            if av[T - 1]:
                run[T - 1] = 1
            for k in range(T - 2, -1, -1):
                if av[k]:
                    run[k] = run[k + 1] + 1
                else:
                    run[k] = 0

            self._avail.append(av)
            self._runlen.append(run)

        any_av = bytearray(T)
        best = array("B", [255]) * T
        for k in range(T):
            maxlen = 0
            idx = 255
            for r in range(self._n_regions):
                if self._avail[r][k]:
                    l = self._runlen[r][k]
                    if l > maxlen:
                        maxlen = l
                        idx = r
            if idx != 255:
                any_av[k] = 1
                best[k] = idx

        next_any = array("I", [T]) * T
        nxt = T
        for k in range(T - 1, -1, -1):
            if any_av[k]:
                nxt = k
            next_any[k] = nxt

        self._any_avail = any_av
        self._best_region = best
        self._next_any = next_any

        self._switch_penalty_steps = max(1, int(math.ceil(float(self.restart_overhead) / gap)))
        self._switch_threshold = self._switch_penalty_steps
        self._critical_slack = 2.0 * float(self.restart_overhead) + 2.0 * gap
        self._pause_buffer = 2.0 * gap

        self._prepared = True

    def _update_progress(self) -> None:
        tdt = self.task_done_time
        l = len(tdt)
        if l > self._done_len:
            self._done_sum += float(sum(tdt[self._done_len:l]))
            self._done_len = l

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_prepared()
        self._update_progress()

        remaining_work = float(self.task_duration) - float(self._done_sum)
        if remaining_work <= 1e-9:
            return ClusterType.NONE

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0))
        time_left = float(self.deadline) - elapsed
        if time_left <= 0:
            return ClusterType.NONE

        gap = float(getattr(self.env, "gap_seconds", 60.0))
        if gap <= 0:
            gap = 60.0

        k = int(elapsed // gap)
        if k < 0:
            k = 0
        if k >= self._T:
            k = self._T - 1

        slack = time_left - remaining_work

        if self._force_ondemand or slack <= self._critical_slack:
            self._force_ondemand = True
            return ClusterType.ON_DEMAND

        cur_region = 0
        try:
            cur_region = int(self.env.get_current_region())
        except Exception:
            cur_region = 0
        if cur_region < 0:
            cur_region = 0
        if cur_region >= self._n_regions:
            cur_region = min(cur_region, self._n_regions - 1)

        any_av = bool(self._any_avail[k]) if self._any_avail is not None else False

        if any_av:
            target = int(self._best_region[k]) if self._best_region is not None else 255
            if target != 255 and 0 <= target < self._n_regions:
                if target != cur_region:
                    do_switch = False
                    if not has_spot:
                        do_switch = True
                    elif last_cluster_type != ClusterType.SPOT:
                        do_switch = True
                    else:
                        if float(getattr(self, "remaining_restart_overhead", 0.0)) <= 0.0:
                            cur_run = int(self._runlen[cur_region][k]) if 0 <= cur_region < self._n_regions else 0
                            best_run = int(self._runlen[target][k])
                            if best_run > cur_run + self._switch_threshold:
                                do_switch = True
                    if do_switch:
                        try:
                            self.env.switch_region(target)
                            cur_region = target
                        except Exception:
                            pass

            # If we didn't switch, trust has_spot; if we did, trust trace.
            # Detect switch by checking whether env current region matches original region.
            switched = False
            try:
                switched = int(self.env.get_current_region()) != int(cur_region)
            except Exception:
                switched = False
            # The above may be unreliable if env.get_current_region failed; compute using original:
            # Use a safer approach: if we requested switch, env should reflect it; otherwise cur_region is original.
            # We'll infer based on whether current region is within bounds and differs from original.
            try:
                env_region = int(self.env.get_current_region())
            except Exception:
                env_region = cur_region
            if env_region != cur_region:
                cur_region = env_region
            spot_ok = bool(self._avail[cur_region][k]) if cur_region != int(getattr(self, "_last_seen_region", cur_region)) else bool(has_spot)
            # Ensure spot_ok uses has_spot if we're still in the original region.
            # Store last seen for next call.
            self._last_seen_region = cur_region

            if spot_ok:
                return ClusterType.SPOT

            # Fallback if something went wrong.
            if slack >= self._pause_buffer + float(self.restart_overhead):
                return ClusterType.NONE
            return ClusterType.ON_DEMAND

        # No spot in any region (per trace); decide wait vs on-demand.
        next_k = int(self._next_any[k]) if self._next_any is not None else self._T
        if next_k >= self._T:
            return ClusterType.ON_DEMAND

        wait_time = float(next_k - k) * gap
        if slack >= wait_time + float(self.restart_overhead) + self._pause_buffer:
            return ClusterType.NONE
        return ClusterType.ON_DEMAND