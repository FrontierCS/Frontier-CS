"""Common module for cant_be_late problem variants."""

# ADRS configuration constants
ADRS_ENV_PATHS = [
    "us-west-2a_k80_8",
    "us-west-2b_k80_1",
    "us-west-2b_k80_8",
    "us-west-2a_v100_1",
    "us-west-2a_v100_8",
    "us-west-2b_v100_1",
]

ADRS_JOB_CONFIGS = [
    {"duration": 48, "deadline": 52},
    {"duration": 48, "deadline": 70},
]

ADRS_CHANGEOVER_DELAYS = [0.02, 0.05, 0.1]
