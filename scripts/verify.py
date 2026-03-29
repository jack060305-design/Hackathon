"""
One-shot project verification: deps, backend import + HTTP, frontend syntax, data JSON, ML predict.
Run from repo root: python scripts/verify.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(cmd: list[str], cwd: Path | None = None) -> None:
    print(f"\n$ {' '.join(cmd)}", flush=True)
    r = subprocess.run(cmd, cwd=cwd or ROOT)
    if r.returncode != 0:
        sys.exit(r.returncode)


def main() -> None:
    os.chdir(ROOT)
    print("Repo:", ROOT, flush=True)

    # --- pip ---
    print("\n=== pip install (backend + frontend) ===", flush=True)
    run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-q",
            "-r",
            str(ROOT / "backend" / "requirements.txt"),
            "-r",
            str(ROOT / "frontend" / "requirements.txt"),
        ]
    )

    # --- backend import ---
    print("\n=== backend: import app.main ===", flush=True)
    r = subprocess.run(
        [sys.executable, "-c", "from app.main import app; assert app.title"],
        cwd=ROOT / "backend",
    )
    if r.returncode != 0:
        sys.exit(r.returncode)
    print("OK: FastAPI app loads", flush=True)

    # --- backend HTTP (uvicorn subprocess) ---
    print("\n=== backend: uvicorn /health ===", flush=True)
    port = 8765
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=ROOT / "backend",
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    url = f"http://127.0.0.1:{port}/health"
    try:
        for _ in range(30):
            time.sleep(0.2)
            try:
                with urllib.request.urlopen(url, timeout=2) as resp:
                    body = resp.read().decode()
                assert resp.status == 200
                print("OK:", url, "->", body[:200], flush=True)
                break
            except (urllib.error.URLError, ConnectionResetError, OSError):
                continue
        else:
            err = proc.stderr.read().decode(errors="replace") if proc.stderr else ""
            proc.terminate()
            print("FAIL: uvicorn did not respond", err[:500], file=sys.stderr)
            sys.exit(1)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    # --- frontend bytecode ---
    print("\n=== frontend: py_compile ===", flush=True)
    fe = ROOT / "frontend"
    for rel in (
        "app.py",
        "county_data.py",
        "views/map.py",
        "views/chatbot.py",
        "views/ocean_tracker.py",
    ):
        p = fe / rel
        if not p.is_file():
            print("MISSING:", p, file=sys.stderr)
            sys.exit(1)
        run([sys.executable, "-m", "py_compile", str(p)])

    # --- data geojson ---
    print("\n=== data: florida_counties.geojson ===", flush=True)
    geo = ROOT / "data" / "florida_counties.geojson"
    with open(geo, encoding="utf-8") as f:
        j = json.load(f)
    assert j.get("type") == "FeatureCollection"
    assert "features" in j
    assert len(j["features"]) == 67
    print("OK: florida_counties.geojson has 67 features", flush=True)

    cp = ROOT / "data" / "florida_county_centroids.json"
    with open(cp, encoding="utf-8") as f:
        cen = json.load(f)
    assert len(cen) == 67
    print("OK: florida_county_centroids.json has 67 counties", flush=True)

    # --- ML ---
    print("\n=== ml: predict.py ===", flush=True)
    model_path = ROOT / "ml" / "models" / "risk_model.pkl"
    if not model_path.is_file():
        print("(no .pkl) running train.py once...", flush=True)
        run([sys.executable, str(ROOT / "ml" / "train.py")])
    subprocess.run(
        [sys.executable, str(ROOT / "ml" / "predict.py")],
        cwd=ROOT,
        check=True,
    )

    print("\n=== ALL CHECKS PASSED ===", flush=True)


if __name__ == "__main__":
    main()
