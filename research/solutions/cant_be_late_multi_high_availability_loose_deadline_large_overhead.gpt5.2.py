import json
import os
from argparse import Namespace
from array import array
from typing import Any, List, Optional, Sequence, Tuple

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


def _as_bool(v: Any) -> int:
    if isinstance(v, bool):
        return 1 if v else 0
    if v is None:
        return 0
    if isinstance(v, (int, float)):
        return 1 if v > 0 else 0
    if isinstance(v, str):
        s = v.strip().lower()
        if not s:
            return 0
        if s in ("1", "true", "t", "yes", "y", "up", "available", "avail", "on"):
            return 1
        if s in ("0", "false", "f", "no", "n", "down", "unavailable", "off"):
            return 0
        try:
            return 1 if float(s) > 0 else 0
        except Exception:
            return 0
    return 0


def _extract_trace_from_json(obj: Any) -> Optional[Sequence[Any]]:
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        preferred_keys = (
            "trace",
            "traces",
            "availability",
            "avail",
            "spot",
            "has_spot",
            "data",
            "series",
            "values",
        )
        for k in preferred_keys:
            if k in obj and isinstance(obj[k], list):
                return obj[k]
        for v in obj.values():
            if isinstance(v, list):
                return v
        # If dict of timestamp->value
        if obj and all(isinstance(k, (str, int, float)) for k in obj.keys()):
            try:
                items = sorted(obj.items(), key=lambda kv: float(kv[0]))
                return [v for _, v in items]
            except Exception:
                pass
    return None


def _load_trace_file(path: str) -> bytearray:
    # Attempt numpy for .npy/.npz if present
    ext = os.path.splitext(path)[1].lower()
    if ext in (".npy", ".npz"):
        try:
            import numpy as np  # type: ignore

            arr = np.load(path, allow_pickle=True)
            if isinstance(arr, np.lib.npyio.NpzFile):  # type: ignore
                keys = list(arr.files)
                if not keys:
                    return bytearray()
                data = arr[keys[0]]
            else:
                data = arr
            flat = data.ravel().tolist()
            return bytearray(_as_bool(x) for x in flat)
        except Exception:
            pass

    try:
        with open(path, "rb") as f:
            raw = f.read()
    except Exception:
        return bytearray()

    # JSON
    raw_strip = raw.lstrip()
    if raw_strip.startswith(b"[") or raw_strip.startswith(b"{"):
        try:
            obj = json.loads(raw_strip.decode("utf-8"))
            seq = _extract_trace_from_json(obj)
            if seq is None:
                return bytearray()
            return bytearray(_as_bool(x) for x in seq)
        except Exception:
            pass

    # Text / CSV
    try:
        text = raw.decode("utf-8", errors="ignore")
    except Exception:
        return bytearray()

    out = bytearray()
    for line in text.splitlines():
        if not line:
            continue
        # Remove comments
        if "#" in line:
            line = line.split("#", 1)[0]
        if not line.strip():
            continue
        line = line.replace(",", " ").replace("\t", " ")
        toks = line.split()
        if not toks:
            continue
        # If multiple cols, assume last is availability
        out.append(_as_bool(toks[-1]))
    return out


class Solution(MultiRegionStrategy):
    NAME = "my_strategy_v2"

    def solve(self, spec_path: str) -> "Solution":
        with open(spec_path) as f:
            config = json.load(f)

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )

        # Load traces for offline multi-region planning (optional; will be validated online).
        self._trace_files: List[str] = []
        self._traces: List[bytearray] = []
        self._runlen: List[array] = []
        self._any_next: Optional[array] = None
        self._trace_len: int = 0
        self._trace_trustworthy: bool = True

        spec_dir = os.path.dirname(os.path.abspath(spec_path))
        trace_files = config.get("trace_files", []) or []
        if isinstance(trace_files, list):
            for p in trace_files:
                if not isinstance(p, str):
                    continue
                full = p if os.path.isabs(p) else os.path.join(spec_dir, p)
                self._trace_files.append(full)
                self._traces.append(_load_trace_file(full))

            lens = [len(t) for t in self._traces if t is not None]
            self._trace_len = min(lens) if lens else 0

            if self._trace_len > 0 and self._traces:
                # Truncate all to min length for safe indexing.
                self._traces = [t[: self._trace_len] for t in self._traces]
                L = self._trace_len

                # Precompute run lengths of consecutive availability starting at t for each region.
                self._runlen = []
                for t in self._traces:
                    rl = array("I", [0]) * (L + 1)
                    # Reverse scan
                    cnt = 0
                    for i in range(L - 1, -1, -1):
                        if t[i]:
                            cnt += 1
                        else:
                            cnt = 0
                        rl[i] = cnt
                    rl[L] = 0
                    self._runlen.append(rl)

                # Precompute next time index where ANY region has spot.
                any_spot = bytearray(L)
                for i in range(L):
                    v = 0
                    for r in range(len(self._traces)):
                        v |= self._traces[r][i]
                        if v:
                            break
                    any_spot[i] = 1 if v else 0

                nxt = array("I", [0]) * (L + 1)
                INF = L + 1
                nxt[L] = INF
                for i in range(L - 1, -1, -1):
                    nxt[i] = i if any_spot[i] else nxt[i + 1]
                self._any_next = nxt
            else:
                self._trace_trustworthy = False
        else:
            self._trace_trustworthy = False

        # Runtime caches
        self._done_sum = 0.0
        self._done_len = 0
        self._committed_on_demand = False
        self._initialized_step = False

        super().__init__(args)
        return self

    def _update_done_sum(self) -> float:
        tdt = self.task_done_time
        if tdt is None:
            self._done_sum = 0.0
            self._done_len = 0
            return 0.0
        n = len(tdt)
        if n < self._done_len:
            # Reset (e.g., new task)
            self._done_sum = float(sum(tdt))
            self._done_len = n
            return self._done_sum
        if n > self._done_len:
            self._done_sum += float(sum(tdt[self._done_len : n]))
            self._done_len = n
        return self._done_sum

    def _trace_has_spot(self, region: int, idx: int) -> bool:
        if not self._trace_trustworthy:
            return False
        if idx < 0:
            return False
        if region < 0 or region >= len(self._traces):
            return False
        t = self._traces[region]
        if idx >= len(t):
            return False
        return bool(t[idx])

    def _pick_best_spot_region(self, idx: int, current_region: int, num_regions: int) -> int:
        best_region = -1
        best_score = -1
        for r in range(num_regions):
            if not self._trace_has_spot(r, idx):
                continue
            score = 1
            if r < len(self._runlen) and idx < len(self._runlen[r]):
                score = int(self._runlen[r][idx])
            # Prefer staying to avoid overhead
            if r == current_region:
                score = score * 4 + 1
            else:
                score = score * 4
            if score > best_score:
                best_score = score
                best_region = r
        return best_region

    def _next_any_spot_wait_steps(self, idx: int) -> int:
        if not self._trace_trustworthy or self._any_next is None:
            return 10**9
        if idx < 0:
            return 10**9
        L = self._trace_len
        if idx >= L:
            return 10**9
        nxt = int(self._any_next[idx])
        if nxt >= L:
            return 10**9
        return nxt - idx

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Initialize / validate trace alignment on first few calls.
        gap = float(getattr(self.env, "gap_seconds", 1.0))
        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0))
        idx = int(elapsed // gap) if gap > 0 else 0

        current_region = int(self.env.get_current_region())
        num_regions = int(self.env.get_num_regions())

        if not self._initialized_step:
            self._initialized_step = True
            # Basic sanity: if trace count mismatches, disable.
            if self._trace_trustworthy and len(self._traces) != num_regions:
                self._trace_trustworthy = False

        # Validate current region's trace against observed has_spot (only if we won't switch before using it).
        if self._trace_trustworthy and 0 <= current_region < len(self._traces) and 0 <= idx < self._trace_len:
            if bool(self._traces[current_region][idx]) != bool(has_spot):
                self._trace_trustworthy = False

        done = self._update_done_sum()
        remaining_work = float(self.task_duration) - done
        if remaining_work <= 0:
            return ClusterType.NONE

        deadline = float(self.deadline)
        remaining_time = deadline - elapsed

        # If we're already late, run on-demand.
        slack = remaining_time - remaining_work
        if slack <= 0:
            self._committed_on_demand = True
            return ClusterType.ON_DEMAND

        # If very close to the deadline, commit to on-demand (avoid extra restarts/idle).
        # Use a conservative buffer for restarts / scheduling granularity.
        restart_overhead = float(self.restart_overhead)
        buffer = restart_overhead + 2.0 * gap
        if slack <= buffer:
            self._committed_on_demand = True

        if self._committed_on_demand:
            return ClusterType.ON_DEMAND

        # Prefer spot if available (potentially in another region).
        if self._trace_trustworthy:
            best_region = self._pick_best_spot_region(idx, current_region, num_regions)
            if best_region != -1:
                # If we're on on-demand, avoid switching if too tight (extra overhead).
                if last_cluster_type == ClusterType.ON_DEMAND and slack <= (restart_overhead + gap):
                    return ClusterType.ON_DEMAND
                if best_region != current_region:
                    self.env.switch_region(best_region)
                return ClusterType.SPOT
        else:
            if has_spot:
                return ClusterType.SPOT

        # No spot available (or can't trust traces). Decide between waiting (NONE) vs on-demand.
        if self._trace_trustworthy:
            wait_steps = self._next_any_spot_wait_steps(idx)
            if wait_steps < 10**8:
                wait_time = wait_steps * gap
                # If waiting is safe even if we later switch to on-demand, do it.
                # Conservative: assume we might need one restart overhead when resuming.
                if wait_time + remaining_work + restart_overhead <= remaining_time:
                    return ClusterType.NONE

        # If can't safely wait, use on-demand. If slack is shrinking, commit.
        if slack <= (restart_overhead + 3.0 * gap):
            self._committed_on_demand = True
        return ClusterType.ON_DEMAND