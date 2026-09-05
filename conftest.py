"""Pytest configuration: ensure AUDIT_SECRET_KEY is set for tests."""
import os

# Provide a deterministic test key when the real one is not configured.
if not os.getenv("AUDIT_SECRET_KEY"):
    os.environ["AUDIT_SECRET_KEY"] = "test-audit-key-news2-qsofa-2026"
