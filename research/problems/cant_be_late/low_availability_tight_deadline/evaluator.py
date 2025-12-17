#!/usr/bin/env python3
"""Thin evaluator for low_availability_tight_deadline variant."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "common"))
from run_evaluator import main

if __name__ == "__main__":
    main(str(Path(__file__).resolve().parent / "resources"))
