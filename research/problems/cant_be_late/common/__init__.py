"""Common module for cant_be_late problem variants."""

# Region configs based on spot availability analysis
# High availability (43% - 78%): us-west-2b_v100_1, us-west-2a_v100_8, us-west-2b_v100_8, us-west-2b_k80_1
# Low availability (4% - 40%): us-west-2a_k80_1, us-west-2a_v100_1, us-west-2b_k80_8, us-west-2a_k80_8

HIGH_AVAILABILITY_REGIONS = [
    "us-west-2b_k80_1",    # 77.5%
    "us-west-2b_v100_8",   # 66.3%
    "us-west-2a_v100_8",   # 62.8%
    "us-west-2b_v100_1",   # 43.2%
]

LOW_AVAILABILITY_REGIONS = [
    "us-west-2a_k80_8",    # 40.3%
    "us-west-2b_k80_8",    # 39.1%
    "us-west-2a_v100_1",   # 30.3%
    "us-west-2a_k80_1",    # 4.3%
]

ALL_REGIONS = HIGH_AVAILABILITY_REGIONS + LOW_AVAILABILITY_REGIONS

# Deadline configs
TIGHT_DEADLINE_CONFIG = [{"duration": 48, "deadline": 52}]  # 4 hours slack
LOOSE_DEADLINE_CONFIG = [{"duration": 48, "deadline": 70}]  # 22 hours slack

# Default overhead
DEFAULT_CHANGEOVER_DELAYS = [0.02]

# Legacy ADRS configs (for backwards compatibility)
ADRS_ENV_PATHS = ALL_REGIONS
ADRS_JOB_CONFIGS = TIGHT_DEADLINE_CONFIG + LOOSE_DEADLINE_CONFIG
ADRS_CHANGEOVER_DELAYS = DEFAULT_CHANGEOVER_DELAYS
