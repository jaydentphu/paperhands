"""Worker entrypoint. APScheduler jobs (daily_run, daily_mark) are wired in Stage 7.

Placeholder for Stage 0b: proves the worker container starts and stays up.
"""

from __future__ import annotations

import time


def main() -> None:
    print("[worker] placeholder running - scheduler jobs wired in Stage 7", flush=True)
    while True:
        time.sleep(60)


if __name__ == "__main__":
    main()
