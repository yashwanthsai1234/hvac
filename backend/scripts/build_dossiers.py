"""Full pipeline: seed → compute → reason → store dossiers.

Usage:
    python -m backend.scripts.build_dossiers [--no-api]
"""

import sys
import time

from backend.db.connection import reset_db, get_db
from backend.scripts.seed_db import seed
from backend.compute import run_compute_engine
from backend.reasoning.dossier_builder import build_and_store_dossier
from backend.reasoning.portfolio_builder import build_and_store_portfolio


def build_all(use_api=True):
    """Run the full pipeline."""
    start = time.time()

    print("\n[PIPELINE] Step 1/4: Resetting and seeding database...")
    reset_db()
    seed()

    print("\n[PIPELINE] Step 2/4: Running compute engine...")
    run_compute_engine()

    print("\n[PIPELINE] Step 3/4: Building project dossiers...")
    db = get_db()
    projects = db.execute("SELECT project_id FROM contracts ORDER BY project_id").fetchall()

    for proj in projects:
        pid = proj["project_id"]
        build_and_store_dossier(pid, use_api=use_api)

    print("\n[PIPELINE] Step 4/4: Building portfolio summary...")
    build_and_store_portfolio()

    # Verify
    dossier_count = db.execute("SELECT COUNT(*) FROM dossiers").fetchone()[0]
    elapsed = time.time() - start

    print(f"\n[PIPELINE] Complete! {dossier_count} dossiers stored in {elapsed:.1f}s")
    print(f"  Database: {db.execute('PRAGMA database_list').fetchone()[2]}")


if __name__ == "__main__":
    use_api = "--no-api" not in sys.argv
    if not use_api:
        print("[PIPELINE] Running without API calls (metrics-based fallback reasoning)")
    build_all(use_api=use_api)
