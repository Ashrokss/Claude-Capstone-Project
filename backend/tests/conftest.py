"""
Shared pytest configuration.

Tests must not depend on whatever happens to be in `.env`. Without this, a
developer with working Supabase credentials runs a different suite from CI:
every app fixture would open a real connection over the network, making the
tests slow, flaky, and dependent on someone's private project.

These assignments happen at import time, before any `app.*` module is loaded,
because `Settings` is instantiated at module scope. Environment variables take
priority over `.env` in pydantic-settings, so this wins.
"""

import os

# A recognised placeholder, so the database layer reports "not configured"
# rather than attempting to dial out.
os.environ["DATABASE_URL"] = "postgresql://user:password@host:port/database_name"

# Auth tests set their own secret via monkeypatch; anything real must not leak in.
os.environ["SUPABASE_JWT_SECRET"] = ""
os.environ["SUPABASE_JWT_AUDIENCE"] = "authenticated"

# Keep CORS expectations stable regardless of local overrides.
os.environ["FRONTEND_URL"] = "http://localhost:3000"
os.environ["EXTRA_CORS_ORIGINS"] = ""
