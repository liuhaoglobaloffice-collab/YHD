import threading
import time
import random
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
import asyncio
from src.ai.providers import ProviderGateway, ModelConfig, ProviderType, MockProvider


def _do_complete(gw, model_id):
    try:
        resp = asyncio.run(
            gw.complete(
                ProviderType.OPENAI,
                model_id,
                [{"role": "user", "content": "ping"}],
                trace_id=uuid4(),
            )
        )
        return resp
    except Exception as e:
        return e


def _do_switch(gw, model_id):
    try:
        gw.switch_model(ProviderType.OPENAI, model_id)
        return True
    except Exception as e:
        return e


def test_concurrent_switch_and_complete(tmp_path, monkeypatch):
    monkeypatch.setenv("MODEL_REGISTRY_DIR", str(tmp_path))

    gw = ProviderGateway()
    gw.register_provider(MockProvider())

    # register several models
    models = [f"m{i}" for i in range(4)]
    for m in models:
        gw.register_model(ModelConfig(provider=ProviderType.OPENAI, model_id=m, model_name=m, context_window=1024))

    # ensure initial active
    assert gw.get_active_model(ProviderType.OPENAI) in models

    # run concurrent switches and completes
    futures = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        for _ in range(20):
            # half switches, half completes
            if random.random() < 0.5:
                mid = random.choice(models)
                futures.append(ex.submit(_do_switch, gw, mid))
            else:
                mid = random.choice(models)
                futures.append(ex.submit(_do_complete, gw, mid))

    results = [f.result() for f in futures]

    # ensure no unexpected exceptions
    for r in results:
        assert not isinstance(r, Exception), f"Background task raised: {r}"

    # persisted active model should be valid
    gw2 = ProviderGateway()
    active = gw2.get_active_model(ProviderType.OPENAI)
    assert active in models
