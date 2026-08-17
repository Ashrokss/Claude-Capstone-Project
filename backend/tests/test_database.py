"""
Unit tests for database URL handling and engine configuration.

These cover the parts that can be checked without a live Supabase: URL
normalisation, driver selection, pooling strategy, and the SSL translation
asyncpg needs. Connectivity itself is exercised by `/health`.
"""

import importlib
import sys

import pytest
from sqlalchemy.engine import make_url

DIRECT = "postgresql://postgres:pw@db.abcdefgh.supabase.co:5432/postgres"
POOLER = "postgresql://postgres.abc:pw@aws-0-ap-south-1.pooler.supabase.com:6543/postgres"
PLACEHOLDER = "postgresql://user:password@host:port/database_name"


@pytest.fixture
def db_module(monkeypatch):
    """Reload app.core.database with a caller-supplied DATABASE_URL."""

    def _load(url: str):
        monkeypatch.setenv("DATABASE_URL", url)
        for name in ("app.core.database", "app.core.config"):
            sys.modules.pop(name, None)
        return importlib.import_module("app.core.database")

    yield _load

    # Leave the modules reloaded from the ambient environment for other tests.
    for name in ("app.core.database", "app.core.config"):
        sys.modules.pop(name, None)


class TestUrlNormalisation:
    def test_direct_url_selects_psycopg2_for_sync(self, db_module):
        db = db_module(DIRECT)
        assert db.get_sync_database_url().startswith("postgresql+psycopg2://")

    def test_direct_url_selects_asyncpg_for_async(self, db_module):
        db = db_module(DIRECT)
        assert db.get_async_database_url().startswith("postgresql+asyncpg://")

    def test_legacy_postgres_scheme_is_normalised(self, db_module):
        db = db_module(DIRECT.replace("postgresql://", "postgres://"))
        assert db.get_sync_database_url().startswith("postgresql+psycopg2://")

    def test_a_hardcoded_driver_suffix_is_replaced(self, db_module):
        # An operator pasting a +asyncpg URL must not break Alembic.
        db = db_module(DIRECT.replace("postgresql://", "postgresql+asyncpg://"))
        assert db.get_sync_database_url().startswith("postgresql+psycopg2://")

    def test_special_characters_in_password_survive(self, db_module):
        db = db_module("postgresql://postgres:p%40ss%3Bword@db.x.supabase.co:5432/postgres")
        assert make_url(db.get_sync_database_url()).password == "p@ss;word"

    def test_non_postgres_url_is_rejected(self, db_module):
        db = db_module("mysql://user:pw@localhost:3306/app")
        with pytest.raises(db.DatabaseNotConfigured):
            db.get_sync_database_url()


class TestPlaceholderHandling:
    def test_placeholder_defers_the_engine_instead_of_crashing(self, db_module):
        db = db_module(PLACEHOLDER)
        assert db.sync_engine is None

    def test_empty_url_is_reported_as_unconfigured(self, db_module):
        db = db_module("")
        with pytest.raises(db.DatabaseNotConfigured):
            db.get_async_database_url()

    def test_unconfigured_is_a_valueerror(self, db_module):
        # main.py and callers catch ValueError; keep that contract.
        db = db_module(PLACEHOLDER)
        assert issubclass(db.DatabaseNotConfigured, ValueError)

    def test_health_check_reports_false_when_unconfigured(self, db_module):
        db = db_module(PLACEHOLDER)
        assert db.test_sync_connection() is False


class TestPoolingStrategy:
    def test_direct_connection_uses_a_real_pool(self, db_module):
        db = db_module(DIRECT)
        assert type(db.sync_engine.pool).__name__ == "QueuePool"
        assert "AsyncAdapted" in type(db.create_async_engine_instance().pool).__name__

    def test_transaction_pooler_disables_client_side_pooling(self, db_module):
        # Layering a pool on top of PgBouncer only holds transaction slots open.
        db = db_module(POOLER)
        assert type(db.sync_engine.pool).__name__ == "NullPool"
        assert type(db.create_async_engine_instance().pool).__name__ == "NullPool"

    def test_pooler_is_detected_by_host_as_well_as_port(self, db_module):
        db = db_module(POOLER.replace(":6543", ":5432"))
        assert type(db.sync_engine.pool).__name__ == "NullPool"


class TestSslModeTranslation:
    @pytest.mark.parametrize(
        ("sslmode", "expected"),
        [("require", "require"), ("verify-full", "verify-full"), ("disable", False),
         ("prefer", "prefer"), ("allow", "prefer")],
    )
    def test_sslmode_maps_onto_asyncpgs_ssl_argument(self, db_module, sslmode, expected):
        db = db_module(f"{DIRECT}?sslmode={sslmode}")
        _, ssl_value = db._split_sslmode(db._base_url())
        assert ssl_value == expected

    def test_sslmode_is_stripped_from_the_async_url(self, db_module):
        # asyncpg has no sslmode keyword; leaving it in raises TypeError.
        db = db_module(f"{DIRECT}?sslmode=require")
        assert "sslmode" not in db.get_async_database_url()

    def test_sslmode_is_kept_on_the_sync_url(self, db_module):
        # psycopg2 speaks libpq and understands it natively.
        db = db_module(f"{DIRECT}?sslmode=require")
        assert "sslmode=require" in db.get_sync_database_url()

    def test_unknown_sslmode_falls_back_to_require(self, db_module):
        db = db_module(f"{DIRECT}?sslmode=banana")
        _, ssl_value = db._split_sslmode(db._base_url())
        assert ssl_value == "require"

    def test_absent_sslmode_leaves_ssl_unset(self, db_module):
        db = db_module(DIRECT)
        _, ssl_value = db._split_sslmode(db._base_url())
        assert ssl_value is None


class TestJobQueueSessionBinding:
    """
    The analysis queue must resolve the session factory at call time.

    `AsyncSessionLocal` is None until `init_async_engine()` runs, and that call
    rebinds the name inside `app.core.database`. A `from ... import` in the queue
    module would capture the None permanently, so every job would die with
    "'NoneType' object is not callable" while the API still reported the claim as
    queued. That failed silently once already.
    """

    def test_queue_does_not_import_the_factory_by_value(self):
        import pathlib

        source = pathlib.Path("app/services/job_queue.py").read_text(encoding="utf-8")
        assert "from app.core.database import AsyncSessionLocal" not in source

    def test_factory_lookup_raises_clearly_when_uninitialised(self, db_module):
        db_module(PLACEHOLDER)
        # Reloaded with no engine, so the factory is absent.
        import importlib
        import sys

        sys.modules.pop("app.services.job_queue", None)
        job_queue = importlib.import_module("app.services.job_queue")

        with pytest.raises(RuntimeError, match="not initialised"):
            job_queue.analysis_queue._session_factory()

    def test_factory_is_found_once_the_engine_is_initialised(self, db_module):
        import importlib
        import sys

        db = db_module(DIRECT)
        sys.modules.pop("app.services.job_queue", None)
        job_queue = importlib.import_module("app.services.job_queue")

        # Stand in for what init_async_engine() assigns at startup.
        db.AsyncSessionLocal = lambda: None
        try:
            assert job_queue.analysis_queue._session_factory() is db.AsyncSessionLocal
        finally:
            db.AsyncSessionLocal = None
            sys.modules.pop("app.services.job_queue", None)
