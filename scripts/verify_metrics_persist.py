import os, importlib, time, sqlite3, traceback, asyncio

try:
    os.environ['METRICS_PERSIST'] = '1'
    # Determine DB path used by project and remove it for a clean test
    import src.database.base as base
    dburl = base.get_database_url()
    dbpath = None
    if dburl.startswith('sqlite'):
        parts = dburl.split('///', 1)
        if len(parts) == 2:
            dbpath = parts[1]
    if dbpath and os.path.exists(dbpath):
        os.remove(dbpath)

    # Ensure model is imported and DB init
    importlib.import_module('src.database.provider_metrics_model')
    asyncio.get_event_loop().run_until_complete(base.init_database())
    print('db_init_done, dbpath=', dbpath)

    # Start app (this will subscribe to lifecycle and start collector)
    import src.api.app as appmod
    app = appmod.create_app()
    from fastapi.testclient import TestClient
    client = TestClient(app)

    # allow background collector a moment to perform first collection
    time.sleep(3)

    r = client.get('/api/v1/providers/metrics')
    print('api_metrics_status', r.status_code, 'items', len(r.json()) if r.status_code==200 else 'err')
    r2 = client.get('/metrics')
    print('prom_metrics_status', r2.status_code)

    # inspect in-memory collected metrics
    import src.api.providers_metrics as pm
    # Force one collection run synchronously to avoid waiting for interval
    try:
        asyncio.get_event_loop().run_until_complete(pm._collect_once())
        print('manual_collect_once_done')
    except Exception as e:
        print('manual_collect_error', e)

    collected = pm.get_latest_metrics()
    print('collected_count', len(collected))

    # try to persist one sample explicitly to see if persistence path works
    if collected:
        first = collected[0]
        provider_key = first.get('provider')
        model = first.get('model')
        samples_map = {model: first.get('points')}
        print('attempting explicit persist for', provider_key, model)
        import src.api.providers_metrics_persist as pmp
        try:
            asyncio.get_event_loop().run_until_complete(pmp.persist_samples(provider_key, samples_map))
            print('explicit persist completed')
        except Exception as e:
            print('explicit_persist_error', e)

    # check DB rows
    if dbpath is None:
        print('No sqlite DB path detected; skipping DB checks')
    else:
        conn = sqlite3.connect(dbpath)
        cur = conn.cursor()
        try:
            cur.execute('SELECT count(*) FROM provider_metric_samples')
            cnt = cur.fetchone()[0]
            print('rows_in_provider_metric_samples', cnt)
            cur.execute('SELECT provider, model, latency_ms, success_rate, timestamp FROM provider_metric_samples ORDER BY id DESC LIMIT 5')
            rows = cur.fetchall()
            print('sample_rows', rows)
        except Exception as e:
            print('db_query_error', e)
        finally:
            conn.close()

except Exception:
    traceback.print_exc()
    print('FAILED')
