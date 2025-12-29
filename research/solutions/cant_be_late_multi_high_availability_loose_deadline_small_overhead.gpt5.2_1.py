import os
import json
import csv
from argparse import Namespace
from typing import Any, Dict, List, Optional, Tuple, Union

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


def _is_number_str(s: str) -> bool:
    try:
        float(s)
        return True
    except Exception:
        return False


def _to_bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if v is None:
        return False
    if isinstance(v, (int, float)):
        return v != 0
    if isinstance(v, str):
        t = v.strip().lower()
        if t in ("1", "true", "t", "yes", "y", "available", "avail", "up"):
            return True
        if t in ("0", "false", "f", "no", "n", "unavailable", "down", "na", "none"):
            return False
        if _is_number_str(t):
            return float(t) != 0.0
    return False


class Solution(MultiRegionStrategy):
    NAME = "smart_wait_switch_v2"

    def solve(self, spec_path: str) -> "Solution":
        with open(spec_path, "r") as f:
            config = json.load(f)

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)

        self._td_sum = 0.0
        self._td_len = 0
        self._forced_ondemand = False
        self._miss_streak = 0
        self._last_seen_region = -1

        self._trace_info: List[Optional[Tuple[List[bool], List[int], List[int], int]]] = []
        self._has_trace = False

        self._region_visits: List[int] = []
        self._region_spot_hits: List[int] = []

        trace_files = config.get("trace_files", [])
        base_dir = os.path.dirname(os.path.abspath(spec_path))
        if isinstance(trace_files, list) and trace_files:
            for p in trace_files:
                try:
                    if not isinstance(p, str):
                        self._trace_info.append(None)
                        continue
                    path = p if os.path.isabs(p) else os.path.join(base_dir, p)
                    avail = self._load_trace(path)
                    if not avail:
                        self._trace_info.append(None)
                        continue
                    self._trace_info.append(self._preprocess_avail(avail))
                    self._has_trace = True
                except Exception:
                    self._trace_info.append(None)

        return self

    def _load_trace(self, path: str) -> List[bool]:
        # Best-effort loader supporting JSON, CSV, or newline-separated values.
        with open(path, "r") as f:
            head = f.read(4096)
            f.seek(0)
            hs = head.lstrip()
            if hs.startswith("[") or hs.startswith("{"):
                try:
                    obj = json.load(f)
                except Exception:
                    f.seek(0)
                    txt = f.read()
                    obj = json.loads(txt)
                return self._extract_avail_from_json(obj)

        # Non-JSON: attempt CSV with header.
        try:
            with open(path, "r", newline="") as f:
                first_line = f.readline()
                if not first_line:
                    return []
                f.seek(0)
                sep = "," if "," in first_line else ("\t" if "\t" in first_line else None)
                if sep is not None:
                    reader = csv.DictReader(f, delimiter=sep)
                    if reader.fieldnames:
                        key = self._pick_avail_key(reader.fieldnames)
                        if key is not None:
                            out: List[bool] = []
                            for row in reader:
                                if row is None:
                                    continue
                                out.append(_to_bool(row.get(key)))
                            if out:
                                return out
        except Exception:
            pass

        # Fallback: parse line by line, last numeric/token.
        out2: List[bool] = []
        with open(path, "r") as f:
            for line in f:
                s = line.strip()
                if not s:
                    continue
                if s[0] in ("#",):
                    continue
                tokens = [t for t in s.replace(",", " ").split() if t]
                if not tokens:
                    continue
                # Prefer last token that looks like boolean/number.
                val = tokens[-1]
                out2.append(_to_bool(val))
        return out2

    def _pick_avail_key(self, fieldnames: List[str]) -> Optional[str]:
        # Choose a likely availability indicator column.
        # Prefer explicit availability-like names.
        candidates: List[Tuple[int, str]] = []
        for name in fieldnames:
            if name is None:
                continue
            n = name.strip().lower()
            score = 0
            if "avail" in n:
                score += 100
            if "spot" in n:
                score += 40
            if "available" in n:
                score += 60
            if "interrupt" in n or "preempt" in n or "termination" in n:
                score -= 30
            if "price" in n or "cost" in n:
                score -= 50
            if n in ("has_spot", "spot", "available", "availability", "is_available"):
                score += 120
            if score != 0:
                candidates.append((score, name))
        if not candidates:
            return None
        candidates.sort(reverse=True)
        return candidates[0][1]

    def _extract_avail_from_json(self, obj: Any) -> List[bool]:
        # Accept common forms:
        # - [0/1, ...]
        # - [{"has_spot": 0/1}, ...]
        # - {"availability": [0/1, ...]} etc.
        if isinstance(obj, list):
            if not obj:
                return []
            if all(isinstance(x, (bool, int, float, str)) for x in obj):
                return [_to_bool(x) for x in obj]
            if all(isinstance(x, dict) for x in obj):
                keys = self._json_avail_keys(obj[0].keys())
                if not keys:
                    return []
                k = keys[0]
                out: List[bool] = []
                for row in obj:
                    if not isinstance(row, dict):
                        continue
                    out.append(_to_bool(row.get(k)))
                return out
            return []

        if isinstance(obj, dict):
            # Find first list-like under plausible keys.
            for k in self._json_avail_keys(obj.keys()):
                v = obj.get(k)
                if isinstance(v, list) and v and all(isinstance(x, (bool, int, float, str)) for x in v):
                    return [_to_bool(x) for x in v]
            # If only one list present, use it.
            for v in obj.values():
                if isinstance(v, list) and v and all(isinstance(x, (bool, int, float, str)) for x in v):
                    return [_to_bool(x) for x in v]
        return []

    def _json_avail_keys(self, keys: Any) -> List[str]:
        preferred = []
        for k in keys:
            if not isinstance(k, str):
                continue
            n = k.strip().lower()
            if n in ("has_spot", "spot", "available", "availability", "is_available", "spot_available"):
                preferred.append(k)
        if preferred:
            return preferred
        fallback = []
        for k in keys:
            if not isinstance(k, str):
                continue
            n = k.strip().lower()
            if "avail" in n and "unavail" not in n:
                fallback.append(k)
            elif "spot" in n and "price" not in n:
                fallback.append(k)
        return fallback

    def _preprocess_avail(self, avail: List[bool]) -> Tuple[List[bool], List[int], List[int], int]:
        L = len(avail)
        INF = L + 10
        next_one = [INF] * (L + 1)
        run_len = [0] * (L + 1)
        next_one[L] = INF
        run_len[L] = 0
        for i in range(L - 1, -1, -1):
            if avail[i]:
                next_one[i] = i
                run_len[i] = 1 + run_len[i + 1]
            else:
                next_one[i] = next_one[i + 1]
                run_len[i] = 0
        return (avail, next_one, run_len, INF)

    def _done_seconds(self) -> float:
        td = self.task_done_time
        n = len(td)
        if n < self._td_len:
            self._td_sum = 0.0
            self._td_len = 0
        if n > self._td_len:
            self._td_sum += float(sum(td[self._td_len : n]))
            self._td_len = n
        return self._td_sum

    def _get_scalar(self, v: Any, default: float = 0.0) -> float:
        if v is None:
            return default
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, (list, tuple)):
            if not v:
                return default
            try:
                return float(v[0])
            except Exception:
                return default
        try:
            return float(v)
        except Exception:
            return default

    def _best_region_by_trace(self, idx: int, num_regions: int) -> Optional[int]:
        if not self._has_trace or not self._trace_info:
            return None
        best = None
        best_wait = 10**18
        best_run = -1

        max_r = min(num_regions, len(self._trace_info))
        for r in range(max_r):
            info = self._trace_info[r]
            if info is None:
                continue
            avail, next_one, run_len, INF = info
            L = len(avail)
            i = idx if idx <= L else L
            nxt = next_one[i] if i < len(next_one) else INF
            if nxt >= INF:
                continue
            wait = nxt - idx
            run = run_len[nxt] if 0 <= nxt < len(run_len) else 0
            if wait < best_wait or (wait == best_wait and run > best_run):
                best_wait = wait
                best_run = run
                best = r
        return best

    def _best_region_by_learning(self, num_regions: int) -> Optional[int]:
        if num_regions <= 1:
            return None
        if not self._region_visits or len(self._region_visits) != num_regions:
            self._region_visits = [0] * num_regions
            self._region_spot_hits = [0] * num_regions
        best = None
        best_score = -1.0
        for r in range(num_regions):
            v = self._region_visits[r]
            h = self._region_spot_hits[r]
            # Laplace smoothing
            score = (h + 1.0) / (v + 2.0)
            if score > best_score:
                best_score = score
                best = r
        return best

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        gap = self._get_scalar(getattr(self.env, "gap_seconds", None), 1.0)
        elapsed = self._get_scalar(getattr(self.env, "elapsed_seconds", None), 0.0)

        deadline = self._get_scalar(getattr(self, "deadline", None), 0.0)
        task_duration = self._get_scalar(getattr(self, "task_duration", None), 0.0)
        restart_overhead = self._get_scalar(getattr(self, "restart_overhead", None), 0.0)

        done = self._done_seconds()
        remaining_work = task_duration - done
        if remaining_work <= 1e-9:
            return ClusterType.NONE

        remaining_time = deadline - elapsed
        if remaining_time <= 1e-9:
            return ClusterType.NONE

        overhead_pending = self._get_scalar(getattr(self, "remaining_restart_overhead", None), 0.0)
        if overhead_pending < 0:
            overhead_pending = 0.0

        slack = remaining_time - remaining_work - overhead_pending

        try:
            num_regions = int(self.env.get_num_regions())
        except Exception:
            num_regions = 1
        if num_regions < 1:
            num_regions = 1

        try:
            cur_region = int(self.env.get_current_region())
        except Exception:
            cur_region = 0

        if not self._region_visits or len(self._region_visits) != num_regions:
            self._region_visits = [0] * num_regions
            self._region_spot_hits = [0] * num_regions
        if 0 <= cur_region < num_regions:
            self._region_visits[cur_region] += 1
            if has_spot:
                self._region_spot_hits[cur_region] += 1

        # If we've committed to on-demand near deadline, stick with it.
        if self._forced_ondemand:
            return ClusterType.ON_DEMAND

        # Conservative forcing threshold to avoid deadline miss.
        force_buffer = 2.0 * gap + max(restart_overhead, 0.0)
        if slack <= force_buffer:
            self._forced_ondemand = True
            return ClusterType.ON_DEMAND

        # Prefer spot whenever available (cheap).
        if has_spot:
            self._miss_streak = 0
            return ClusterType.SPOT

        # No spot: decide whether to wait (NONE) or use on-demand.
        self._miss_streak += 1

        # Try to switch region while waiting, but avoid doing so when overhead is pending.
        if num_regions > 1 and overhead_pending <= 1e-9:
            idx = int(elapsed // gap) if gap > 0 else 0
            target = self._best_region_by_trace(idx, num_regions)
            if target is None:
                # Switch only occasionally when blind, to avoid thrashing.
                if self._miss_streak in (1, 10, 30):
                    target = self._best_region_by_learning(num_regions)
            if target is not None and 0 <= target < num_regions and target != cur_region:
                try:
                    self.env.switch_region(int(target))
                except Exception:
                    pass

        # Wait if we can afford at least one full timestep; otherwise progress on on-demand.
        if slack >= gap + max(restart_overhead, 0.0):
            return ClusterType.NONE
        return ClusterType.ON_DEMAND