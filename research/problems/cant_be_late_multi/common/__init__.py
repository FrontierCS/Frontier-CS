"""Configuration for cant_be_late_multi variants."""

# Task duration (hours)
TASK_DURATION_HOURS = 24

# Deadline configurations (hours)
TIGHT_DEADLINE = 36  # 12-hour slack
LOOSE_DEADLINE = 48  # 24-hour slack

# Restart overhead configurations (hours)
SMALL_OVERHEAD = 0.05  # 3 minutes
LARGE_OVERHEAD = 0.20  # 12 minutes

# High availability scenarios (east coast regions with good availability)
HIGH_AVAILABILITY_SCENARIOS = [
    {"name": "2_zones_same_region", "regions": ["us-east-1a_v100_1", "us-east-1c_v100_1"], "traces": [f"{i}.json" for i in range(8)]},
    {"name": "2_regions_east_west", "regions": ["us-east-2a_v100_1", "us-west-2a_v100_1"], "traces": [f"{i}.json" for i in range(8)]},
    {"name": "3_regions_diverse", "regions": ["us-east-1a_v100_1", "us-east-2b_v100_1", "us-west-2c_v100_1"], "traces": [f"{i}.json" for i in range(6)]},
    {"name": "3_zones_same_region", "regions": ["us-east-1a_v100_1", "us-east-1c_v100_1", "us-east-1d_v100_1"], "traces": [f"{i}.json" for i in range(6)]},
    {"name": "5_regions_high_diversity", "regions": ["us-east-1a_v100_1", "us-east-1f_v100_1", "us-west-2a_v100_1", "us-west-2b_v100_1", "us-east-2b_v100_1"], "traces": [f"{i}.json" for i in range(4)]},
    {"name": "all_9_regions", "regions": ["us-east-2a_v100_1", "us-west-2c_v100_1", "us-east-1d_v100_1", "us-east-2b_v100_1", "us-west-2a_v100_1", "us-east-1f_v100_1", "us-east-1a_v100_1", "us-west-2b_v100_1", "us-east-1c_v100_1"], "traces": [f"{i}.json" for i in range(2)]}
]

# Low availability scenarios (west coast regions with lower availability)
LOW_AVAILABILITY_SCENARIOS = [
    {"name": "2_zones_west", "regions": ["us-west-2a_v100_1", "us-west-2b_v100_1"], "traces": [f"{i}.json" for i in range(8)]},
    {"name": "3_zones_west", "regions": ["us-west-2a_v100_1", "us-west-2b_v100_1", "us-west-2c_v100_1"], "traces": [f"{i}.json" for i in range(6)]},
    {"name": "2_regions_west_east2", "regions": ["us-west-2a_v100_1", "us-east-2a_v100_1"], "traces": [f"{i}.json" for i in range(8)]},
    {"name": "5_regions_mixed", "regions": ["us-west-2a_v100_1", "us-west-2b_v100_1", "us-west-2c_v100_1", "us-east-2a_v100_1", "us-east-2b_v100_1"], "traces": [f"{i}.json" for i in range(4)]},
]

# Stage 1 quick check scenario
STAGE_1_SCENARIO = {
    "name": "stage_1_quick_check",
    "regions": ["us-east-1a_v100_1", "us-east-1c_v100_1"],
    "traces": ["0.json"]
}

# Timeout for evaluation
TIMEOUT_SECONDS = 300
WORST_POSSIBLE_SCORE = -1e9
