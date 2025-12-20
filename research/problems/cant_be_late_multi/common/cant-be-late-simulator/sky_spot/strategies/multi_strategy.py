# sky_spot/strategies/multi_strategy.py

import logging
import typing
from typing import Optional

import configargparse  # Import necessary for type hinting
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

if typing.TYPE_CHECKING:
    from sky_spot import env
    from sky_spot import task

logger = logging.getLogger(__name__)


class MultiRegionStrategy(Strategy):
    """
    Base class for multi-region strategies.
    It correctly handles migration overhead on top of standard restart costs.
    """

    NAME = 'multi_region_strategy'

    def __init__(self, args: configargparse.Namespace):
        super().__init__(args)
        self.last_startup_region: Optional[int] = None
        self.migration_overhead_seconds = getattr(args, 'region_switch_overhead_hours', 0.0) * 3600
        if self.migration_overhead_seconds > 0:
            logger.info(f'Migration cost (region switch overhead) is set to {self.migration_overhead_seconds} seconds.')

    @classmethod
    def _from_args(cls, parser: "configargparse.ArgumentParser") -> "MultiRegionStrategy":
        """
        The factory method that defines ALL necessary arguments for this strategy
        and its parents. Any subclass will inherit this complete method.
        """
        group = parser.add_argument_group(cls.NAME)
        
        # 1. Argument required by THIS class
        group.add_argument(
            "--region-switch-overhead-hours",
            type=float,
            default=0.0,
            help="Overhead of region switching in hours.",
        )

        # 2. Argument required by the TOP-LEVEL base class (Strategy)
        group.add_argument(
            '--inter-task-overhead',
            type=float,
            default=[0.0],
            nargs='+',
            help='(Required by base class) Overhead for switching between sub-tasks.'
        )
        
        args, _ = parser.parse_known_args()
        return cls(args)

    def _before_decision_hook(self, last_cluster_type: ClusterType, request_type: ClusterType):
        if self._should_add_migration_overhead(last_cluster_type, request_type):
            self._add_migration_overhead()

    def _should_add_migration_overhead(self, last_cluster_type: ClusterType, request_type: ClusterType) -> bool:
        """
        Check if we should add the *additional* migration overhead.
        
        This should only happen when starting a VM (from a NONE state) in a
        different region than the last one.
        """
        # Only consider adding overhead when a new VM is starting.
        if last_cluster_type != ClusterType.NONE or request_type == ClusterType.NONE:
            return False
        if not hasattr(self.env, 'get_current_region'):
            return False
        current_region = self.env.get_current_region()
        if self.last_startup_region is None:
            self.last_startup_region = current_region
            return False
        if current_region == self.last_startup_region:
            return False
        return True

    def _add_migration_overhead(self):
        """
        Adds ONLY the additional migration cost to the already calculated restart overhead.
        """
        if self.migration_overhead_seconds > 0:
            logger.info(
                f"Cross-region startup detected. Adding {self.migration_overhead_seconds}s migration cost "
                f"to the current remaining overhead of {self.remaining_restart_overhead}s."
            )
            self.remaining_restart_overhead += self.migration_overhead_seconds
            logger.info(f"New total overhead: {self.remaining_restart_overhead}s")
        self.last_startup_region = self.env.get_current_region()