"""
Database utility functions for VeriClaim AI MVP.

This module provides helper functions for database operations like
connection testing, migrations, and schema verification.
"""

import asyncio
import sys
import logging
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.core.database import (
    test_sync_connection,
    test_async_connection,
    sync_engine,
    SyncSessionLocal,
    init_async_engine,
    close_async_engine,
)
from app.models.base import Base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_connections():
    """Test both sync and async database connections."""
    print("\n" + "=" * 60)
    print("VeriClaim AI MVP - Database Connection Test")
    print("=" * 60)

    print(f"\nDatabase URL (masked): {settings.database_url.split('@')[0]}@***")
    print(f"App Mode: {'DEBUG' if settings.debug else 'PRODUCTION'}")
    print(f"Demo Mode: {settings.demo_mode}\n")

    # Test synchronous connection
    print("1. Testing Synchronous Connection...")
    sync_result = test_sync_connection()
    if sync_result:
        print("   ✓ Synchronous connection successful\n")
    else:
        print("   ✗ Synchronous connection failed\n")

    # Test asynchronous connection
    print("2. Testing Asynchronous Connection...")
    try:
        await init_async_engine()
        async_result = await test_async_connection()
        if async_result:
            print("   ✓ Asynchronous connection successful\n")
        else:
            print("   ✗ Asynchronous connection failed\n")
        await close_async_engine()
    except Exception as e:
        print(f"   ✗ Asynchronous connection failed: {str(e)}\n")
        async_result = False

    # Summary
    print("=" * 60)
    if sync_result and async_result:
        print("✓ All database connections are working correctly!")
        print("=" * 60)
        return True
    else:
        print("✗ One or more database connections failed.")
        print("=" * 60)
        return False


def verify_models():
    """Verify that all SQLAlchemy models are properly defined."""
    print("\n" + "=" * 60)
    print("VeriClaim AI MVP - Model Verification")
    print("=" * 60 + "\n")

    # Import all models to register them
    try:
        # Models will be imported here when they are created
        # For now, just show the base model
        print("Base Model Information:")
        print(f"  - Base metadata tables: {list(Base.metadata.tables.keys())}")
        if not Base.metadata.tables:
            print("  ℹ No models defined yet (expected during initial setup)")
        print("\nTo add new models, import them in app/models/__init__.py")
        print("=" * 60)
        return True
    except Exception as e:
        print(f"✗ Error verifying models: {str(e)}")
        print("=" * 60)
        return False


async def main():
    """Run all database tests."""
    try:
        # Test connections
        connection_ok = await test_connections()

        # Verify models
        models_ok = verify_models()

        # Overall result
        print("\n" + "=" * 60)
        if connection_ok and models_ok:
            print("✓ Database setup is ready!")
            sys.exit(0)
        else:
            print("⚠ Some checks failed. Review the output above.")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n✗ Database setup interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error during database setup: {str(e)}")
        logger.exception("Detailed error:")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
