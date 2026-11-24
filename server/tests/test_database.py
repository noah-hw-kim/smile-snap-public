from database import normalize_database_url
from db_models import Base


def test_normalize_neon_pooled_url():
    """Neon pooled URIs must convert to asyncpg and move sslmode/channel_binding to connect_args."""
    raw = "postgresql://user:pass@ep-cool-123-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

    clean_url, connect_args = normalize_database_url(raw)

    assert clean_url == "postgresql+asyncpg://user:pass@ep-cool-123-pooler.us-east-1.aws.neon.tech/neondb"
    assert connect_args == {"statement_cache_size": 0, "ssl": True}


def test_normalize_legacy_postgres_scheme():
    """Legacy postgres:// URIs must also normalize to postgresql+asyncpg://."""
    raw = "postgres://user:pass@db.example.com:5432/app"

    clean_url, connect_args = normalize_database_url(raw)

    assert clean_url == "postgresql+asyncpg://user:pass@db.example.com:5432/app"
    assert connect_args == {"statement_cache_size": 0, "ssl": True}


def test_normalize_sslmode_disable():
    """Local Postgres URLs with sslmode=disable must not enable SSL in connect_args."""
    raw = "postgresql://test:test@localhost:5432/testdb?sslmode=disable"

    clean_url, connect_args = normalize_database_url(raw)

    assert clean_url == "postgresql+asyncpg://test:test@localhost:5432/testdb"
    assert connect_args == {"statement_cache_size": 0}


def test_normalize_preserves_other_query_params():
    """Non-libpq query parameters must stay intact after stripping sslmode/channel_binding."""
    raw = "postgresql://user:pass@host/db?sslmode=require&channel_binding=require&application_name=smile_snap"

    clean_url, connect_args = normalize_database_url(raw)

    assert clean_url == "postgresql+asyncpg://user:pass@host/db?application_name=smile_snap"
    assert connect_args == {"statement_cache_size": 0, "ssl": True}


def test_schema_metadata_tables_and_cascade_fks():
    """SQLAlchemy Base metadata must define users, photos, diary_entries with CASCADE FKs."""
    assert set(Base.metadata.tables.keys()) == {"users", "photos", "diary_entries"}

    for table_name in ("photos", "diary_entries"):
        fks = list(Base.metadata.tables[table_name].foreign_keys)
        assert len(fks) == 1
        assert fks[0].column.table.name == "users"
        assert fks[0].column.name == "user_id"
        assert fks[0].ondelete == "CASCADE"
