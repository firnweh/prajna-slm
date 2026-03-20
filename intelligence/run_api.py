#!/usr/bin/env python3
"""
Entry-point launcher for PRAJNA Intelligence API.
Run from the repo root: python3 intelligence/run_api.py
"""
import sys
import os

# Inject intelligence/ onto path so bare imports (from services.xxx, from config.xxx)
# resolve correctly regardless of the working directory.
INTELLIGENCE_DIR = os.path.dirname(os.path.abspath(__file__))
if INTELLIGENCE_DIR not in sys.path:
    sys.path.insert(0, INTELLIGENCE_DIR)

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "services.api.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        reload_dirs=[INTELLIGENCE_DIR],
        log_level="info",
    )
