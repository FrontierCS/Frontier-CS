import json
import math
import os
import re
from argparse import Namespace
from array import array
from typing import Any, List, Optional, Sequence, Tuple, Union

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_multi_region_v1"

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

        base_dir = os.path.dirname(os.path.abspath(spec_path))
        trace_files = config.get("trace_files", []) or []
        self._trace_paths: List[str] = []
        for p in trace_files:
            if not isinstance(p, str):
                continue
            p2 = p
            if not os.path.isabs(p2):
                p2 = os.path.join(base_dir, p2)
            self._trace_paths.append(p2)

        self._raw_traces: List[Any] = []
        for p in self._trace_paths:
            try:
                self._raw_traces.append(self._read_trace_file(p))
            except Exception:
                self._raw_traces.append([])

        self._prepared = False
        self._avail: List[bytearray] = []
        self._run_len: List[array] = []

        self._gap_s = None
        self._deadline_s = None
        self._task_duration_s = None
        self._restart_overhead_s = None

        self._done_accum = 0.0
        self._done_len = 0
        self._emergency = False
        return self

    @staticmethod
    def _to_bool(v: Any) -> int:
        if v is None:
            return 0
        if isinstance(v, bool):
            return 1 if v else 0
        if isinstance(v, (int, float)):
            return 1 if float(v) > 0.0 else 0
        if isinstance(v, str):
            s = v.strip().lower()
            if not s:
                return 0
            if s in ("1", "true", "t", "yes", "y", "on"):
                return 1
            if s in ("0", "false", "f", "no", "n", "off"):
                return 0
            try:
                return 1 if float(s) > 0.0 else 0
            except Exception:
                return 0
        return 0

    def _extract_sequence_from_json(self, obj: Any) -> Any:
        if isinstance(obj, list):
            if not obj:
                return []
            if all(isinstance(x, (int, float, bool, str)) or x is None for x in obj):
                return obj
            if all(isinstance(x, (list, tuple)) and len(x) >= 2 for x in obj):
                return obj
            flat = []
            for x in obj:
                if isinstance(x, (int, float, bool, str)) or x is None:
                    flat.append(x)
                elif isinstance(x, dict):
                    for k in ("spot", "availability", "available", "has_spot", "value", "val", "x"):
                        if k in x:
                            flat.append(x[k])
                            break
                elif isinstance(x, (list, tuple)) and len(x) >= 1:
                    flat.append(x[-1])
            return flat
        if isinstance(obj, dict):
            for k in (
                "trace",
                "traces",
                "availability",
                "availabilities",
                "spot_availability",
                "spot_avail",
                "has_spot",
                "values",
                "data",
                "series",
                "records",
            ):
                if k in obj and isinstance(obj[k], list):
                    return self._extract_sequence_from_json(obj[k])
            for v in obj.values():
                if isinstance(v, list):
                    return self._extract_sequence_from_json(v)
            return []
        return []

    def _read_trace_file(self, path: str) -> Any:
        with open(path, "r") as f:
            text = f.read()

        s = text.strip()
        if not s:
            return []

        if s[0] in "[{":
            try:
                obj = json.loads(s)
                seq = self._extract_sequence_from_json(obj)
                return seq if seq is not None else []
            except Exception:
                pass

        # Text/CSV-ish parsing.
        lines = s.splitlines()
        values: List[Any] = []
        pairs: List[Tuple[float, Any]] = []
        saw_pair = False

        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith("#") or line.startswith("//"):
                continue
            if "#" in line:
                line = line.split("#", 1)[0].strip()
            if not line:
                continue
            toks = re.split(r"[,\s]+", line.strip())
            toks = [t for t in toks if t]
            if not toks:
                continue

            if len(toks) >= 2:
                try:
                    t0 = float(toks[0])
                    v0 = toks[1]
                    pairs.append((t0, v0))
                    saw_pair = True
                    continue
                except Exception:
                    pass

            if not saw_pair:
                for t in toks:
                    values.append(t)

        if saw_pair and pairs:
            pairs.sort(key=lambda x: x[0])
            return pairs
        return values

    def _align_trace(self, raw: Any, horizon: int, gap_s: float, deadline_s: float) -> bytearray:
        out = bytearray(horizon)
        if not raw:
            return out

        # Timestamp/value pairs
        if isinstance(raw, list) and raw and isinstance(raw[0], (list, tuple)) and len(raw[0]) >= 2:
            try:
                pairs = [(float(x[0]), x[1]) for x in raw if isinstance(x, (list, tuple)) and len(x) >= 2]
                if not pairs:
                    return out
                pairs.sort(key=lambda x: x[0])
                last_ts = pairs[-1][0]

                # Guess units
                # If timestamps look like hours (ending near deadline_hours), convert to seconds.
                if deadline_s > 0:
                    deadline_h = deadline_s / 3600.0
                    if 0.25 * deadline_h <= last_ts <= 4.0 * deadline_h:
                        pairs = [(ts * 3600.0, v) for ts, v in pairs]

                j = 0
                cur = 0
                # If first ts > 0, default 0 until then.
                for i in range(horizon):
                    t = i * gap_s
                    while j + 1 < len(pairs) and pairs[j + 1][0] <= t:
                        j += 1
                    if pairs[j][0] <= t:
                        cur = self._to_bool(pairs[j][1])
                    out[i] = cur
                return out
            except Exception:
                return out

        # Scalar list
        if not isinstance(raw, list):
            return out

        vals = [self._to_bool(x) for x in raw]
        if not vals:
            return out

        L = len(vals)
        if L == horizon:
            out[:] = bytearray(vals)
            return out
        if L == horizon + 1:
            out[:] = bytearray(vals[:horizon])
            return out

        # Try integer-ish resampling
        if L < horizon:
            ratio = horizon / float(L)
            k = int(round(ratio))
            if k >= 1 and abs(ratio - k) < 0.05:
                idx = 0
                for v in vals:
                    end = idx + k
                    if end >= horizon:
                        end = horizon
                    if idx >= horizon:
                        break
                    out[idx:end] = bytes([v]) * (end - idx)
                    idx = end
                return out

        if L > horizon:
            ratio2 = L / float(horizon)
            k2 = int(round(ratio2))
            if k2 >= 1 and abs(ratio2 - k2) < 0.05:
                for i in range(horizon):
                    out[i] = vals[min(L - 1, i * k2)]
                return out

        # Fallback: truncate/pad with last
        n = min(L, horizon)
        out[:n] = bytearray(vals[:n])
        if n < horizon:
            out[n:] = bytes([vals[-1]]) * (horizon - n)
        return out

    def _lazy_prepare(self) -> None:
        if self._prepared:
            return

        self._gap_s = float(self.env.gap_seconds)
        self._deadline_s = float(self.deadline)
        self._restart_overhead_s = float(self.restart_overhead)
        try:
            self._task_duration_s = float(self.task_duration)
        except Exception:
            self._task_duration_s = float(self.task_duration[0])

        if self._gap_s <= 0:
            self._gap_s = 1.0

        horizon = int(math.ceil(self._deadline_s / self._gap_s)) + 4
        if horizon < 8:
            horizon = 8

        num_regions = int(self.env.get_num_regions())
        n_traces = min(num_regions, len(self._raw_traces)) if self._raw_traces else 0

        self._avail = []
        self._run_len = []

        for r in range(num_regions):
            raw = self._raw_traces[r] if r < n_traces else []
            av = self._align_trace(raw, horizon, self._gap_s, self._deadline_s)
            self._avail.append(av)
            rl = array("I", [0]) * (horizon + 1)
            run = 0
            for i in range(horizon - 1, -1, -1):
                if av[i]:
                    run += 1
                    rl[i] = run
                else:
                    run = 0
                    rl[i] = 0
            rl[horizon] = 0
            self._run_len.append(rl)

        self._prepared = True

    def _update_done_accum(self) -> None:
        td = self.task_done_time
        try:
            n = len(td)
        except Exception:
            self._done_accum = float(td) if td is not None else 0.0
            self._done_len = 0
            return

        if n < self._done_len:
            self._done_accum = float(sum(td)) if n else 0.0
            self._done_len = n
            return

        if n > self._done_len:
            self._done_accum += float(sum(td[self._done_len : n]))
            self._done_len = n

    def _time_index(self, elapsed_s: float) -> int:
        g = self._gap_s
        if g <= 0:
            return 0
        return int((elapsed_s + 1e-9) // g)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._lazy_prepare()
        self._update_done_accum()

        done = self._done_accum
        remaining_work = self._task_duration_s - done
        if remaining_work <= 1e-6:
            return ClusterType.NONE

        elapsed = float(self.env.elapsed_seconds)
        remaining_time = self._deadline_s - elapsed
        if remaining_time <= 1e-9:
            return ClusterType.NONE

        # Emergency logic: ensure feasibility if we commit to on-demand now.
        if last_cluster_type == ClusterType.ON_DEMAND:
            overhead_to_commit = float(self.remaining_restart_overhead)
        else:
            overhead_to_commit = self._restart_overhead_s

        max_work_if_commit = remaining_time - overhead_to_commit
        emergency_buffer = max(2.0 * self._restart_overhead_s, 2.0 * self._gap_s)

        if max_work_if_commit < remaining_work + 1e-6:
            self._emergency = True
        else:
            if (max_work_if_commit - remaining_work) < emergency_buffer:
                self._emergency = True

        if self._emergency:
            # Do not region-switch in emergency mode.
            if has_spot and last_cluster_type == ClusterType.SPOT:
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND

        # Normal mode: opportunistically use spot across regions.
        t = self._time_index(elapsed)
        num_regions = int(self.env.get_num_regions())
        if not self._run_len or num_regions <= 0:
            if has_spot:
                return ClusterType.SPOT
            # Idle if safe, else on-demand.
            rem_after_idle = remaining_time - self._gap_s
            if rem_after_idle > 0 and (rem_after_idle - self._restart_overhead_s) >= remaining_work + emergency_buffer:
                return ClusterType.NONE
            return ClusterType.ON_DEMAND

        # Find region with best consecutive spot run from now.
        best_region = 0
        best_run = 0
        max_r = min(num_regions, len(self._run_len))
        if t < 0:
            t = 0
        for r in range(max_r):
            run = self._run_len[r][t] if t < len(self._run_len[r]) else 0
            if run > best_run:
                best_run = run
                best_region = r

        if best_run <= 0:
            # No spot anywhere; idle if safe, else on-demand.
            rem_after_idle = remaining_time - self._gap_s
            if rem_after_idle > 0 and (rem_after_idle - self._restart_overhead_s) >= remaining_work + emergency_buffer:
                return ClusterType.NONE
            return ClusterType.ON_DEMAND

        curr_region = int(self.env.get_current_region())
        curr_run = 0
        if 0 <= curr_region < max_r and t < len(self._run_len[curr_region]):
            curr_run = self._run_len[curr_region][t]

        switched = False
        target_region = curr_region

        if curr_region != best_region:
            # Switch if current region has no spot OR if it meaningfully extends uninterrupted spot run.
            if curr_run == 0 or ((best_run - curr_run) * self._gap_s) > self._restart_overhead_s:
                target_region = best_region
                switched = True

        will_restart = switched or (last_cluster_type != ClusterType.SPOT)

        # If we would restart, ensure the expected contiguous spot window is long enough to pay back overhead in progress.
        if will_restart:
            expected_window_s = float(best_run) * self._gap_s if target_region == best_region else float(curr_run) * self._gap_s
            if expected_window_s <= self._restart_overhead_s + 1e-9:
                # Avoid burning money/time on a too-short spot window.
                rem_after_idle = remaining_time - self._gap_s
                if rem_after_idle > 0 and (rem_after_idle - self._restart_overhead_s) >= remaining_work + emergency_buffer:
                    return ClusterType.NONE
                return ClusterType.ON_DEMAND

        if switched and target_region != curr_region:
            self.env.switch_region(target_region)

        return ClusterType.SPOT