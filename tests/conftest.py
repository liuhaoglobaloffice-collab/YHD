"""
Test configuration and fixtures.

Resets global database engine caches between tests so that a change of
DATABASE_URL (via env_setup / tmp_path) is always picked up by every
engine factory.  Without this, the three independent _engine globals in
the project would remain pinned to the database file of whichever test
ran first, causing "no such column" errors when the schema has evolved.
"""

import pytest


@pytest.fixture(autouse=True)
def _reset_database_engines():
    """Reset cached database engines before each test.

    Three modules each maintain their own global ``_engine`` variable:

    * ``src.identity.database``
    * ``src.database.base``
    * ``src.api.dependencies.database``

    The FastAPI app uses the identity engine for auth/audit/approval
    routes and the API engine for the rest.  Both must be cleared so
    that a new ``DATABASE_URL`` is reflected in a fresh engine + schema.
    """
    # pylint: disable=import-outside-toplevel
    import src.identity.database as ident_db
    import src.database.base as base_db
    import src.api.dependencies.database as api_db

    # Reset the global variables so get_engine() will create fresh ones
    # pointing to the current DATABASE_URL.
    ident_db._engine = None
    ident_db._async_session_maker = None
    base_db._engine = None
    base_db._session_factory = None
    api_db._engine = None
    api_db._async_session_factory = None

    yield