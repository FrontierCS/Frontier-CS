# Cant-Be-Late Multi-Region Scheduling Problem

Multi-region cloud spot instance scheduling benchmark with multiple difficulty variants.

## Variants

This problem has **8 variants** combining three dimensions:

| Dimension | Options | Description |
|-----------|---------|-------------|
| **Availability** | `high_availability` | East coast regions with good spot availability |
| | `low_availability` | West coast regions with lower spot availability |
| **Deadline** | `tight_deadline` | 36 hours (12-hour slack) |
| | `loose_deadline` | 48 hours (24-hour slack) |
| **Overhead** | `small_overhead` | 0.05 hours (3 minutes) restart overhead |
| | `large_overhead` | 0.20 hours (12 minutes) restart overhead |

### Variant Examples

| Variant | Deadline | Overhead | Regions |
|---------|----------|----------|---------|
| `high_availability_loose_deadline_large_overhead` | 48h (24h slack) | 0.20h (12 min) | East coast |
| `high_availability_loose_deadline_small_overhead` | 48h (24h slack) | 0.05h (3 min) | East coast |
| `high_availability_tight_deadline_large_overhead` | 36h (12h slack) | 0.20h (12 min) | East coast |
| `high_availability_tight_deadline_small_overhead` | 36h (12h slack) | 0.05h (3 min) | East coast |
| `low_availability_loose_deadline_large_overhead` | 48h (24h slack) | 0.20h (12 min) | West coast |
| `low_availability_loose_deadline_small_overhead` | 48h (24h slack) | 0.05h (3 min) | West coast |
| `low_availability_tight_deadline_large_overhead` | 36h (12h slack) | 0.20h (12 min) | West coast |
| `low_availability_tight_deadline_small_overhead` | 36h (12h slack) | 0.05h (3 min) | West coast |

## Multi-Region Feature

Unlike single-region cant_be_late, this problem allows:
- Switching between multiple AWS regions at each timestep
- Each region has different spot availability patterns
- Switching regions forces a restart overhead

## Evaluation Scenarios

**Stage 1**: Quick check on 2-region scenario (must pass to proceed)

**Stage 2**: Full evaluation on multiple scenarios:
- 2 zones same region (8 traces)
- 2 regions east-west (8 traces)
- 3 regions diverse (6 traces)
- 3 zones same region (6 traces)
- 5 regions high diversity (4 traces)
- All 9 regions (2 traces)

## Directory Structure

```
cant_be_late_multi/
├── common/                     # Shared evaluator code
│   ├── __init__.py            # Configuration definitions
│   ├── run_evaluator.py       # Main evaluation logic
│   └── cant-be-late-simulator/  # Simulator with multi-region support
├── {variant}/                  # Each variant directory
│   ├── evaluator.py           # Thin wrapper importing from common/
│   ├── readme                 # Problem specification and API
│   ├── config.yaml            # Variant configuration
│   └── resources/             # Resources for evaluation
└── README.md                  # This file
```

## Common Parameters

All variants share:
- Task duration: 24 hours
- On-demand price: ~$3.06/hr
- Spot price: ~$0.97/hr
- Time limit: 300 seconds
- 9 available AWS regions
