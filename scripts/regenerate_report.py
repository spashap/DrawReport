"""Manually re-run the report pipeline for one order (any status except 'created').

Run: venv/Scripts/python.exe scripts/regenerate_report.py ORDER_ID
Calls jobs.run_order; the public_token (and /r/<token> link) is preserved.
"""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app import jobs
from app.db import connect, init_db


def main() -> int:
    if len(sys.argv) != 2 or not sys.argv[1].isdigit():
        print("usage: regenerate_report.py ORDER_ID")
        return 2
    order_id = int(sys.argv[1])
    init_db()
    conn = connect()
    status = jobs.run_order(conn, order_id)
    print(f"order {order_id} -> {status}")
    return 0 if status in ("delivered", "insufficient") else 1


if __name__ == "__main__":
    raise SystemExit(main())
