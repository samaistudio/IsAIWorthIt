"""Shared test setup: the 10 fictional demo businesses, written to a temporary folder."""
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.smb_metrics import export_all  # noqa: E402


def demo_web():
    """A temporary web folder with data/businesses/*.json, like `python3 isaiworthit.py` creates."""
    tmp = Path(tempfile.mkdtemp(prefix="iaw-test-"))
    export_all(tmp / "data" / "businesses")
    (tmp / "data" / "connectors.json").write_text("[]")
    return tmp


def load(web, slug):
    return json.loads((web / "data" / "businesses" / f"{slug}.json").read_text())
