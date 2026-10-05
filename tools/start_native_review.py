#!/usr/bin/env python3
"""Start the native real-agent console from an extracted source ZIP."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from scopedact.incident_lab.native import main

if __name__ == '__main__':
    main()
