# Phase 2.1 Provider Adapter Layer Acceptance Report

## Scope

Phase 2.1 introduces a lightweight LLM provider abstraction on top of the existing provider scaffold while keeping the Supplier Risk assessment compatibility path intact.

## Implemented changes

- Added `src/providers/llm_base.py` with `LLMProvider` abstract interface supporting `chat()`, `generate()`, and `embeddings()`.
- Added `src/providers/openai.py` with a deterministic `OpenAIProvider` adapter scaffold.
- Added `src/providers/self_host.py` with a deterministic `SelfHostProvider` adapter scaffold.
- Updated `src/providers/mock.py` so `MockRiskAssessmentProvider` also carries the `chat()/generate()/embeddings()` compatibility methods required by the new LLM contract without breaking `analyze()`.
- Updated `src/providers/registry.py` to normalize provider names (`openai`, `self_host`, `self-host`, `selfhost`) and return the correct provider class by registry key.
- Updated `src/providers/__init__.py` to export the new provider surface.
- Added `tests/providers/test_provider_switching.py` verifying `mock -> openai -> self_host` interface parity.

## Verification

Command:

```
pytest tests/providers -q
```

Result:

- 1 passed

Full regression command:

```
pytest -q
```

Result:

- Full suite passes with 0 failures.
- Existing warnings remain from Pydantic v2 `class Config` deprecation, `min_items` deprecation, and SQLAlchemy `datetime.utcnow()` deprecation paths. They are warnings only.

## Gate

The Phase 2.1 provider scaffold is accepted for extension into Phase 2.2 Embedding Pipeline.
