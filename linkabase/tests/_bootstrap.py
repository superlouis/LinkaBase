"""Make application modules available to standalone test scripts."""
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(PROJECT / "src"), str(PROJECT / "service")]
