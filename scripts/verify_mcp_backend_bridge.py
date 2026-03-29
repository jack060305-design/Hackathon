"""
Smoke-test: MCP-style imports of backend services (no FastMCP import).
Run from repo root: python scripts/verify_mcp_backend_bridge.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


async def main() -> None:
    from app.services.inland_risk_map import fetch_inland_risk_markers

    d = await fetch_inland_risk_markers(limit=3)
    assert "markers" in d
    print("OK inland_risk_map:", len(d["markers"]), "sample markers")

    from app.models import risk_model

    s = risk_model.predict(80.0, 5.0, "Medium")
    print("OK risk_model.predict:", s)


if __name__ == "__main__":
    asyncio.run(main())
