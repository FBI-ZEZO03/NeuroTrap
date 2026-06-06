"""Shared pytest fixtures."""

import sys
import os

# Ensure src/ is on the path when running tests from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
