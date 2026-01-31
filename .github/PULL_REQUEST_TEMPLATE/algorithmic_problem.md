---
name: Algorithmic Problem Contribution
about: Add a new algorithmic problem to Frontier-CS
title: '[Algorithmic] Add Problem {id}'
labels: algorithmic-problem
---

## Problem Overview

**Problem ID**:
**Category**: <!-- optimization / construction / interactive -->
**Difficulty**: <!-- easy / medium / hard -->

### Description
<!-- Brief description of the problem -->


## Checklist

### Required Files
- [ ] `statement.txt` - Problem description
- [ ] `config.yaml` - Time/memory limits, test count
- [ ] `testdata/` - At least one public test case (1.in, 1.ans)
- [ ] `chk.cc` or `interactor.cc` - Checker or interactor
- [ ] `reference.cpp` - Reference solution **(required for CI)**

### Problem Structure
```
algorithmic/problems/{id}/
├── statement.txt
├── config.yaml
├── reference.cpp    # Required: CI will validate this achieves score > 0
├── testdata/
│   ├── 1.in
│   └── 1.ans
└── chk.cc (or interactor.cc)
```

### Testing
- [ ] Verified checker/interactor compiles
- [ ] Tested with sample solution
- [ ] **Reference solution (`reference.cpp`) achieves score > 0**

## Additional Notes
<!-- Any additional context or special requirements -->

