from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "safe_spot_fallback"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if self.env.elapsed_seconds == 0:
            return ClusterType.SPOT if has_spot else ClusterType.ON_DEMAND
        if last_cluster_type == ClusterType.ON_DEMAND:
            return ClusterType.ON_DEMAND
        if last_cluster_type == ClusterType.SPOT:
            return ClusterType.SPOT if has_spot else ClusterType.ON_DEMAND
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
