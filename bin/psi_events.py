#!/usr/bin/env python3
"""Emit one JSON event per cycle with PSI pressure per resource."""
import sys

from psi_common import discover, emit


def main():
    emit(discover())
    return 0


if __name__ == "__main__":
    sys.exit(main())
