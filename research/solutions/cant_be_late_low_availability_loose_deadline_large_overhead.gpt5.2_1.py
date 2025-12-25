import math
import json
from typing import Any, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cbl_hybrid_v1"

    def __init__(self, *args, **kwargs):
        self._args = args[0] if args else None
        try:
            super().__init__(*args, **kwargs)
        except TypeError:
            super().__init__()

        self._mode = "SPOT_ONLY"  # SPOT_ONLY -> HYBRID -> OD_ONLY
        self._params_inited = False

        # Spot availability stats
        self._steps = 0
        self._spot_steps = 0
        self._u2a_transitions = 0
        self._last_has_spot: Optional[bool] = None

        self._spot_avail_streak_s = 0.0
        self._spot_unavail_streak_s = 0.0

        # Cluster streak stats (based on last_cluster_type argument)
        self._od_streak_s = 0.0
        self._spot_cluster_streak_s = 0.0

        # Tunables (initialized once env/task params exist)
        self._min_spot_only_seconds = 2.0 * 3600.0
        self._od_only_slack_threshold_s = 3.0 * 3600.0
        self._hybrid_spot_slack_min_s = 5.0 * 3600.0
        self._switch_to_spot_after_s = 40.0 * 60.0
        self._min_od_before_spot_s = 12.0 * 60.0

        self._hard_margin_s = 20.0 * 60.0
        self._soft_margin_s = 40.0 * 60.0
        self._overhead_factor = 1.25
        self._z = 1.645  # ~95% one-sided
        self._alpha = 2.0
        self._beta = 6.0

    def solve(self, spec_path: str) -> "Solution":
        # Optional configuration if a spec is provided.
        # Keep robust: ignore parsing failures.
        try:
            if spec_path:
                with open(spec_path, "r", encoding="utf-8") as f:
                    raw = f.read().strip()
                if raw:
                    try:
                        cfg = json.loads(raw)
                    except Exception:
                        cfg = None
                    if isinstance(cfg, dict):
                        v = cfg.get("min_spot_only_hours")
                        if isinstance(v, (int, float)) and v >= 0:
                            self._min_spot_only_seconds = float(v) * 3600.0
                        v = cfg.get("od_only_slack_hours")
                        if isinstance(v, (int, float)) and v >= 0:
                            self._od_only_slack_threshold_s = float(v) * 3600.0
        except Exception:
            pass
        return self

    @staticmethod
    def _wilson_lower(p_hat: float, n: float, z: float) -> float:
        if n <= 0:
            return 0.0
        denom = 1.0 + (z * z) / n
        center = p_hat + (z * z) / (2.0 * n)
        rad = z * math.sqrt(max(0.0, (p_hat * (1.0 - p_hat) + (z * z) / (4.0 * n)) / n))
        return max(0.0, min(1.0, (center - rad) / denom))

    def _get_gap_s(self) -> float:
        gap = getattr(getattr(self, "env", None), "gap_seconds", None)
        if isinstance(gap, (int, float)) and gap > 0:
            return float(gap)
        return 300.0

    def _work_done_seconds(self) -> float:
        td = getattr(self, "task_done_time", None)
        if td is None:
            return 0.0
        if isinstance(td, (int, float)):
            return max(0.0, float(td))

        task_dur = getattr(self, "task_duration", None)
        task_dur = float(task_dur) if isinstance(task_dur, (int, float)) else None

        if isinstance(td, (list, tuple)):
            if not td:
                return 0.0

            # If list of numbers: could be segment lengths OR cumulative.
            if all(isinstance(x, (int, float)) for x in td):
                nums = [float(x) for x in td]
                s = sum(nums)
                done_cum = 0.0
                if len(nums) >= 2 and all(nums[i] <= nums[i + 1] + 1e-9 for i in range(len(nums) - 1)):
                    last = nums[-1]
                    if task_dur is None:
                        # Heuristic: if sum is much larger than last, likely segment lengths.
                        done_cum = last
                    else:
                        if last <= task_dur + 1e-6:
                            done_cum = last
                if done_cum > 0.0:
                    if task_dur is not None:
                        return max(0.0, min(done_cum, task_dur))
                    return max(0.0, done_cum)
                if task_dur is not None:
                    return max(0.0, min(s, task_dur))
                return max(0.0, s)

            # If list of tuples/lists: try interpret as (start, end) windows or durations
            total = 0.0
            for x in td:
                if isinstance(x, (int, float)):
                    total += float(x)
                elif isinstance(x, (list, tuple)):
                    if len(x) >= 2 and isinstance(x[0], (int, float)) and isinstance(x[1], (int, float)):
                        total += float(x[1]) - float(x[0])
                    elif len(x) == 1 and isinstance(x[0], (int, float)):
                        total += float(x[0])
            if task_dur is not None:
                return max(0.0, min(total, task_dur))
            return max(0.0, total)

        return 0.0

    def _remaining_work_s(self) -> float:
        dur = getattr(self, "task_duration", None)
        if not isinstance(dur, (int, float)):
            return 0.0
        done = self._work_done_seconds()
        rem = float(dur) - done
        return 0.0 if rem <= 0 else rem

    def _init_params_if_needed(self) -> None:
        if self._params_inited:
            return
        ro = getattr(self, "restart_overhead", 0.0)
        ro = float(ro) if isinstance(ro, (int, float)) and ro >= 0 else 0.0

        # Delay switching OD->SPOT until spot has been stable long enough to amortize a restart.
        self._switch_to_spot_after_s = max(30.0 * 60.0, 3.0 * ro)
        self._min_od_before_spot_s = max(10.0 * 60.0, 1.0 * ro)

        # Near the deadline, stop taking spot risk.
        self._od_only_slack_threshold_s = max(2.0 * 3600.0, 10.0 * ro)

        # In hybrid mode, avoid switching to spot if slack is already small.
        self._hybrid_spot_slack_min_s = max(4.0 * 3600.0, 15.0 * ro)

        # Safety margins
        gap = self._get_gap_s()
        self._hard_margin_s = max(2.0 * gap, 1.0 * ro, 15.0 * 60.0)
        self._soft_margin_s = max(4.0 * gap, 2.0 * ro, 30.0 * 60.0)

        self._params_inited = True

    def _update_stats(self, last_cluster_type: ClusterType, has_spot: bool) -> None:
        gap = self._get_gap_s()

        self._steps += 1
        if has_spot:
            self._spot_steps += 1

        if self._last_has_spot is not None and (not self._last_has_spot) and has_spot:
            self._u2a_transitions += 1
        self._last_has_spot = has_spot

        if has_spot:
            self._spot_avail_streak_s += gap
            self._spot_unavail_streak_s = 0.0
        else:
            self._spot_unavail_streak_s += gap
            self._spot_avail_streak_s = 0.0

        if last_cluster_type == ClusterType.ON_DEMAND:
            self._od_streak_s += gap
        else:
            self._od_streak_s = 0.0

        if last_cluster_type == ClusterType.SPOT:
            self._spot_cluster_streak_s += gap
        else:
            self._spot_cluster_streak_s = 0.0

    def _spot_p_lower(self) -> float:
        # Beta prior smoothing + Wilson lower bound on the smoothed Bernoulli.
        n = float(self._steps)
        k = float(self._spot_steps)
        n_eff = n + self._alpha + self._beta
        k_eff = k + self._alpha
        p_hat = 0.0 if n_eff <= 0 else (k_eff / n_eff)
        return self._wilson_lower(p_hat, n_eff, self._z)

    def _lambda_u2a_upper_per_s(self, elapsed_s: float) -> float:
        # Transitions from unavailable->available.
        # Prior: 1 transition per ~5 hours.
        elapsed_h = max(1e-6, elapsed_s / 3600.0)
        lam_h = (float(self._u2a_transitions) + 1.0) / (elapsed_h + 5.0)
        lam_h *= 1.5  # upper-ish
        return lam_h / 3600.0

    def _spot_only_pess_progress_s(self, time_left_s: float, has_spot: bool, last_cluster_type: ClusterType) -> float:
        # Pessimistic progress if we run SPOT when available and NONE when unavailable.
        elapsed_s = getattr(getattr(self, "env", None), "elapsed_seconds", 0.0)
        elapsed_s = float(elapsed_s) if isinstance(elapsed_s, (int, float)) and elapsed_s >= 0 else 0.0

        p_lower = self._spot_p_lower()
        lam_u = self._lambda_u2a_upper_per_s(elapsed_s)

        # Expected starts in remaining window: u->a transitions. Plus possible immediate start.
        starts = lam_u * max(0.0, time_left_s)

        # If spot is available now but we are not currently on spot, starting now likely costs an overhead.
        if has_spot and last_cluster_type != ClusterType.SPOT:
            starts += 1.0

        overhead = starts * float(getattr(self, "restart_overhead", 0.0) or 0.0) * self._overhead_factor
        prog = p_lower * time_left_s - overhead
        return max(0.0, prog)

    def _should_switch_od_to_spot_in_hybrid(self, slack_s: float, has_spot: bool) -> bool:
        if not has_spot:
            return False
        if slack_s <= self._hybrid_spot_slack_min_s:
            return False
        if self._spot_avail_streak_s < self._switch_to_spot_after_s:
            return False
        if self._od_streak_s < self._min_od_before_spot_s:
            return False
        return True

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._init_params_if_needed()
        self._update_stats(last_cluster_type, has_spot)

        remaining_work_s = self._remaining_work_s()
        if remaining_work_s <= 0.0:
            return ClusterType.NONE

        elapsed_s = getattr(getattr(self, "env", None), "elapsed_seconds", 0.0)
        elapsed_s = float(elapsed_s) if isinstance(elapsed_s, (int, float)) else 0.0

        deadline_s = getattr(self, "deadline", None)
        if not isinstance(deadline_s, (int, float)):
            # Fallback: if no deadline is available, be safe and run on-demand.
            return ClusterType.ON_DEMAND
        deadline_s = float(deadline_s)

        time_left_s = deadline_s - elapsed_s
        if time_left_s <= 0.0:
            return ClusterType.NONE

        slack_s = time_left_s - remaining_work_s

        # Hard safety: if we're close to the latest possible on-demand completion, go OD_ONLY.
        ro = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        overhead_start_od = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else ro
        if time_left_s <= remaining_work_s + overhead_start_od + self._hard_margin_s:
            self._mode = "OD_ONLY"
        elif slack_s <= self._od_only_slack_threshold_s:
            self._mode = "OD_ONLY"
        else:
            if self._mode == "SPOT_ONLY":
                # Give spot a short chance early on to avoid premature OD when spot comes back soon.
                if elapsed_s >= self._min_spot_only_seconds:
                    pess_prog = self._spot_only_pess_progress_s(time_left_s, has_spot, last_cluster_type)
                    if pess_prog < remaining_work_s + self._soft_margin_s:
                        self._mode = "HYBRID"
                # If spot has been down a long while and slack is shrinking, start making progress.
                if (not has_spot) and self._spot_unavail_streak_s >= 2.0 * 3600.0 and slack_s <= 12.0 * 3600.0:
                    self._mode = "HYBRID"

            elif self._mode == "HYBRID":
                # If spot has been down too long and slack isn't huge, don't risk further.
                if (not has_spot) and self._spot_unavail_streak_s >= 6.0 * 3600.0 and slack_s <= 8.0 * 3600.0:
                    self._mode = "OD_ONLY"

        if self._mode == "OD_ONLY":
            return ClusterType.ON_DEMAND

        if self._mode == "HYBRID":
            if not has_spot:
                return ClusterType.ON_DEMAND

            # Prefer to keep running spot if already on it and it's available.
            if last_cluster_type == ClusterType.SPOT:
                return ClusterType.SPOT

            # Decide whether to switch OD->SPOT.
            if last_cluster_type == ClusterType.ON_DEMAND:
                if self._should_switch_od_to_spot_in_hybrid(slack_s, has_spot):
                    return ClusterType.SPOT
                return ClusterType.ON_DEMAND

            # If previously NONE (or unknown), use spot only if stable; else OD to ensure progress.
            if self._spot_avail_streak_s >= self._switch_to_spot_after_s and slack_s > self._hybrid_spot_slack_min_s:
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND

        # SPOT_ONLY
        if has_spot:
            return ClusterType.SPOT
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)