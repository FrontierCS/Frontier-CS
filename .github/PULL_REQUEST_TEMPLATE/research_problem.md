---
name: Research Problem Contribution
about: Add a new research problem to Frontier-CS
title: '[Research] Add {problem_name}'
labels: research-problem
---

## Problem Overview

**Problem Name**:
**Category**: <!-- os / hpc / ai / db / pl / security -->
**Difficulty**: <!-- easy / medium / hard -->

### Description
<!-- Brief description of the problem (2-3 sentences) -->


### Why This Problem?
<!-- What makes this problem interesting/challenging for frontier models? -->


## Checklist

### Required Files
- [ ] `config.yaml` - Dependencies, datasets, runtime config
- [ ] `readme` - Problem description with API specification
- [ ] `set_up_env.sh` - Environment setup script
- [ ] `evaluate.sh` - Evaluation entry point
- [ ] `evaluator.py` - Scoring logic (outputs 0-100 score)
- [ ] `resources/` - Problem-specific code/data
- [ ] `reference.py` - Reference solution **(required for CI)**

### Problem Structure
```
research/{problem_name}/
├── config.yaml
├── readme
├── set_up_env.sh
├── evaluate.sh
├── evaluator.py
├── reference.py     # Required: CI will validate this achieves score > 0
└── resources/
    └── ...
```

### Testing
- [ ] Verified `set_up_env.sh` runs successfully
- [ ] Verified `evaluate.sh` runs and outputs a numeric score
- [ ] **Reference solution (`reference.py`) achieves score > 0**

**Test Results** (if available):
```
Baseline solution score:
Test environment:
```

## Additional Notes
<!-- Any additional context, known issues, or special requirements -->

