from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .engine import evaluate, make_snapshot, write_snapshot


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path)
    parser.add_argument("--date", default=datetime.now(ZoneInfo("Asia/Seoul")).date().isoformat())
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    config = json.loads((root / "config" / "indicators.json").read_text(encoding="utf-8"))
    fixture = json.loads(args.fixture.read_text(encoding="utf-8")) if args.fixture else None
    snapshot = make_snapshot(config, evaluate(config, fixture), args.date)
    write_snapshot(root, snapshot)
    summary = snapshot["summary"]
    print(json.dumps({"as_of": args.date, "overall": summary["overall"], "macro": summary["macro"], "ai": summary["ai"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

