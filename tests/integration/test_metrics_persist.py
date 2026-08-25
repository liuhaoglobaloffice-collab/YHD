import os
import importlib
import sqlite3
import asyncio
import time

import pytest
from fastapi.testclient import TestClient

# Integration test for metrics persistence

def test_metrics_persist_end_to_end(tmp_path):
    # Ensure METRICS_PERSIST enabled for this test
    os.environ['METRICS_PERSIST'] = '1'

    # Use a temporary sqlite DB for CI-friendly test: set DATABASE_URL before importing project modules
    db_file = tmp_path / 'liuhao_ai_os_test.db'
    os.environ['DATABASE_URL'] = f"sqlite:///{db_file.as_posix()}"

    # Use project's config to find DB path and remove any pre-existing DB for clean run
    import src.database.base as base

    dburl = base.get_database_url()
    dbpath = None
    if dburl.startswith('sqlite'):
        parts = dburl.split('///', 1)
        if len(parts) == 2:
            dbpath = parts[1]

    if dbpath and os.path.exists(dbpath):
        os.remove(dbpath)

    # Import model so it is registered
    importlib.import_module('src.database.provider_metrics_model')

    # Initialize DB
    asyncio.get_event_loop().run_until_complete(base.init_database())

    # Create app and test client
    import src.api.app as appmod
    app = appmod.create_app()
    client = TestClient(app)

    # Manually trigger one collection run to avoid waiting for interval
    import src.api.providers_metrics as pm
    asyncio.get_event_loop().run_until_complete(pm._collect_once())

    # Attempt explicit persist call to ensure the persistence helper works
    collected = pm.get_latest_metrics()
    assert isinstance(collected, list)
    assert len(collected) > 0

    first = collected[0]
    provider_key = first.get('provider')
    model = first.get('model')
    samples_map = {model: first.get('points')}

    import src.api.providers_metrics_persist as pmp
    asyncio.get_event_loop().run_until_complete(pmp.persist_samples(provider_key, samples_map))

    # Ensure DB rows exist
    assert dbpath is not None
    conn = sqlite3.connect(dbpath)
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM provider_metric_samples")
    cnt = cur.fetchone()[0]
    conn.close()
    assert cnt > 0
