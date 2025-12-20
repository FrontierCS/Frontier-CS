# Cant-Be-Late Scheduling Problem

Cloud spot instance scheduling benchmark with multiple difficulty variants.

## Variants

This problem has **12 variants** combining three dimensions:

| Dimension | Options | Description |
|-----------|---------|-------------|
| **Availability** | `high_availability` | 43-78% spot availability regions |
| | `low_availability` | 4-40% spot availability regions |
| | `mixed_availability` | Both high and low availability regions |
| **Deadline** | `tight_deadline` | 52 hours (4-hour slack) |
| | `loose_deadline` | 70 hours (22-hour slack) |
| **Overhead** | `small_overhead` | 0.05 hours (3 minutes) restart overhead |
| | `large_overhead` | 0.20 hours (12 minutes) restart overhead |

### Variant Examples

| Variant | Deadline | Overhead | Regions |
|---------|----------|----------|---------|
| `high_availability_loose_deadline_large_overhead` | 70h (22h slack) | 0.20h (12 min) | High (43-78%) |
| `high_availability_loose_deadline_small_overhead` | 70h (22h slack) | 0.05h (3 min) | High (43-78%) |
| `high_availability_tight_deadline_large_overhead` | 52h (4h slack) | 0.20h (12 min) | High (43-78%) |
| `high_availability_tight_deadline_small_overhead` | 52h (4h slack) | 0.05h (3 min) | High (43-78%) |
| `low_availability_loose_deadline_large_overhead` | 70h (22h slack) | 0.20h (12 min) | Low (4-40%) |
| `low_availability_loose_deadline_small_overhead` | 70h (22h slack) | 0.05h (3 min) | Low (4-40%) |
| `low_availability_tight_deadline_large_overhead` | 52h (4h slack) | 0.20h (12 min) | Low (4-40%) |
| `low_availability_tight_deadline_small_overhead` | 52h (4h slack) | 0.05h (3 min) | Low (4-40%) |
| `mixed_availability_loose_deadline_large_overhead` | 70h (22h slack) | 0.20h (12 min) | Mixed |
| `mixed_availability_loose_deadline_small_overhead` | 70h (22h slack) | 0.05h (3 min) | Mixed |
| `mixed_availability_tight_deadline_large_overhead` | 52h (4h slack) | 0.20h (12 min) | Mixed |
| `mixed_availability_tight_deadline_small_overhead` | 52h (4h slack) | 0.05h (3 min) | Mixed |

## Region Details

**High Availability Regions** (43-78% spot availability):
- `us-west-2b_k80_1` (77.5%)
- `us-west-2b_v100_8` (66.3%)
- `us-west-2a_v100_8` (62.8%)
- `us-west-2b_v100_1` (43.2%)

**Low Availability Regions** (4-40% spot availability):
- `us-west-2a_k80_8` (40.3%)
- `us-west-2b_k80_8` (39.1%)
- `us-west-2a_v100_1` (30.3%)
- `us-west-2a_k80_1` (4.3%)

## Directory Structure

```
cant_be_late/
├── common/                     # Shared evaluator code
│   ├── __init__.py            # Region and config definitions
│   ├── run_evaluator.py       # Main evaluation logic
│   ├── cbl_evaluator.py       # Core simulation evaluator
│   ├── sim_worker.py          # Simulation worker
│   ├── cant-be-late-simulator/  # Simulator code
│   └── real_traces.tar.gz     # Trace data (extracted by set_up_env.sh)
├── {variant}/                  # Each variant directory
│   ├── evaluator.py           # Thin wrapper importing from common/
│   ├── readme                 # Problem specification and API
│   ├── config.yaml            # Variant configuration
│   └── resources/             # Resources for evaluation
└── README.md                  # This file
```

## Common Parameters

All variants share:
- Task duration: 48 hours
- On-demand price: ~$3.06/hr
- Spot price: ~$0.97/hr
- Time limit: 300 seconds
