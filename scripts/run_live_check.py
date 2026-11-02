"""Opt-in local test entry point; never prints credentials."""
import os
import subprocess
import sys

if __name__ == "__main__":
    os.environ["SHEETPILOT_LIVE_META_TEST"] = "1"
    raise SystemExit(subprocess.call([sys.executable, "-m", "pytest", "tests_app/test_live_meta.py",
                                     "-v", "--basetemp=work/pytest-live-manual", "--tb=short"]))
