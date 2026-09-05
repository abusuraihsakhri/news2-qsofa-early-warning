#!/usr/bin/env python3
"""CLI for NEWS2 + qSOFA Early Warning Score Calculator."""
import os
import sys

# Ensure a default audit key is available for direct CLI invocation.
# In production, set AUDIT_SECRET_KEY to a strong random value.
if not os.getenv("AUDIT_SECRET_KEY"):
    os.environ["AUDIT_SECRET_KEY"] = "cli-default-audit-key-news2-qsofa"

from news2_qsofa import main

if __name__ == "__main__":
    sys.exit(main())
