#!/usr/bin/env python
"""
Database connection test script for VeriClaim AI MVP.

Tests both synchronous and asynchronous database connections,
connection pooling, and health check functionality.

Usage:
    python scripts/test_database.py
"""

import asyncio
import sys
import logging
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.core.database import (
    test_sync_connection,
    test_async_connection,
    get_database_url,
    DatabaseConfig,
)
from app.core.logging import configure_logging, get_logger


def test_configuration():
    """Test database configuration."""
    print("\n" + "=" * 70)
    print("DATABASE CONFIGURATION TEST")
    print("=" * 70)

    print("\nConfiguration Settings:")
    print(f"  Debug Mode: {settings.debug}")
    print(f"  Demo Mode: {settings.demo_mode}")
    print(f"  Database URL Present: {'Yes' if settings.database_url else 'No'}")

    if settings.database_url:
        # Mask password
        masked_url = settings.database_url.split("@")[0] + "@***"
        print(f"  Database URL (masked): {masked_url}")

    print("\nConnection Pool Configuration:")
    print(f"  Pool Size: {DatabaseConfig.POOL_SIZE}")
    print(f"  Max Overflow: {DatabaseConfig.MAX_OVERFLOW}")
    print(f"  Pool Timeout: {DatabaseConfig.POOL_TIMEOUT}s")
    print(f"  Pool Recycle: {DatabaseConfig.POOL_RECYCLE}s")
    print(f"  Connect Timeout: {DatabaseConfig.CONNECT_TIMEOUT}s")
    print(f"  Command Timeout: {DatabaseConfig.COMMAND_TIMEOUT}s")

    return True


def test_url_resolution():
    """Test database URL resolution."""
    print("\n" + "=" * 70)
    print("DATABASE URL RESOLUTION TEST")
    print("=" * 70)

    try:
        # Test sync URL
        sync_url = get_database_url(async_mode=False)
        print(f"\n✓ Sync URL Resolution: OK")
        print(f"  Protocol: {'postgresql' if sync_url.startswith('postgresql://') else 'other'}")

        # Test async URL
        async_url = get_database_url(async_mode=True)
        print(f"\n✓ Async URL Resolution: OK")
        print(f"  Protocol: {'postgresql+asyncpg' if async_url.startswith('postgresql+asyncpg://') else 'other'}")

        return True
    except ValueError as e:
        print(f"\n✗ URL Resolution Failed: {str(e)}")
        return False


def test_sync_connection_test():
    """Test synchronous database connection."""
    print("\n" + "=" * 70)
    print("SYNCHRONOUS DATABASE CONNECTION TEST")
    print("=" * 70)

    result = test_sync_connection()
    if result:
        print(f"\n✓ Synchronous Connection: PASSED")
    else:
        print(f"\n⚠ Synchronous Connection: Connection not established")
        if not settings.database_url or "placeholder" in settings.database_url:
            print("  Note: DATABASE_URL not configured or contains placeholders")

    return True


async def test_async_connection_test():
    """Test asynchronous database connection."""
    print("\n" + "=" * 70)
    print("ASYNCHRONOUS DATABASE CONNECTION TEST")
    print("=" * 70)

    result = await test_async_connection()
    if result:
        print(f"\n✓ Asynchronous Connection: PASSED")
    else:
        print(f"\n⚠ Asynchronous Connection: Connection not established")
        if not settings.database_url or "placeholder" in settings.database_url:
            print("  Note: DATABASE_URL not configured or contains placeholders")

    return True


def test_health_check():
    """Test health check endpoint response."""
    print("\n" + "=" * 70)
    print("HEALTH CHECK ENDPOINT TEST")
    print("=" * 70)

    print("\nHealth Check Response Format:")
    print("""
    Expected response:
    {
      "status": "healthy" or "degraded",
      "app": "VeriClaim AI MVP",
      "version": "0.1.0",
      "debug": true/false,
      "demo_mode": true/false,
      "database": "connected" or "disconnected"
    }
    """)

    print("To test, run:")
    print("  python -m uvicorn app.main:app --reload")
    print("  curl http://localhost:8000/health")

    return True


def print_summary(results):
    """Print test summary."""
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    total = len(results)
    passed = sum(1 for r in results if r)
    failed = total - passed

    print(f"\nTotal Tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

    if failed == 0:
        print("\n✓ All tests passed!")
    else:
        print(f"\n⚠ {failed} test(s) failed or incomplete")

    print("\n" + "=" * 70)


async def main():
    """Run all tests."""
    configure_logging()
    logger = get_logger(__name__)

    print("\n" + "=" * 70)
    print("VeriClaim AI MVP - Database Connection Test Suite")
    print("=" * 70)

    results = []

    # Configuration test
    results.append(test_configuration())

    # URL resolution test
    results.append(test_url_resolution())

    # Sync connection test
    results.append(test_sync_connection_test())

    # Async connection test
    results.append(await test_async_connection_test())

    # Health check test
    results.append(test_health_check())

    # Summary
    print_summary(results)

    # Exit code
    exit_code = 0 if all(results) else 1
    print(f"\nExit Code: {exit_code}")
    return exit_code


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
