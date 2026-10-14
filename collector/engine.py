from __future__ import annotations

import csv
import io
import json
import math
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


USER_AGENT = "mingo-risk-monitor/1.0 contact: github-actions"


@dataclass
class Observation:
    value: float | None
    observed_at: str | None
    fetched_at: str
    source_url: str
    verified: bool
    error: str | None = None


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def fetch_text(url: str, timeout: int = 20) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8")


def collect(source: dict[str, Any]) -> Observation:
    fetched_at = utc_now()
    url = source["url"]
    try:
        body = fetch_text(url)
        if source["type"] == "fred_csv":
            rows = list(csv.DictReader(io.StringIO(body)))
            value_key = source["series"]
            valid = [r for r in rows if r.get(value_key) not in (None, "", ".")]
            if not valid:
                raise ValueError("no numeric observations")
            row = valid[-1]
            return Observation(float(row[value_key]), row.get("DATE", row.get("observation_date")), fetched_at, url, True)
        if source["type"] == "json_path":
            payload: Any = json.loads(body)
            for part in source["path"]:
                payload = payload[int(part)] if isinstance(payload, list) else payload[part]
            observed_at = None
            if source.get("date_path"):
                date_value: Any = json.loads(body)
                for part in source["date_path"]:
                    date_value = date_value[int(part)] if isinstance(date_value, list) else date_value[part]
                observed_at = str(date_value)
            return Observation(float(payload), observed_at, fetched_at, url, True)
        raise ValueError(f"unsupported source type: {source['type']}")
    except Exception as exc:  # collector failure must become B, never a guessed status
        return Observation(None, None, fetched_at, url, False, f"{type(exc).__name__}: {exc}")


def classify(value: float | None, rule: dict[str, Any], verified: bool) -> tuple[str, str]:
    if not verified or value is None or not math.isfinite(value):
        return "B", "수집 실패 또는 검증 불가"
    direction = rule.get("direction", "higher_is_worse")
    amber = float(rule["amber"])
    red = float(rule["red"])
    if direction == "higher_is_worse":
        status = "R" if value >= red else "A" if value >= amber else "G"
    elif direction == "lower_is_worse":
        status = "R" if value <= red else "A" if value <= amber else "G"
    else:
        return "B", "지원하지 않는 판정 방향"
    return status, f"관측값 {value:g}; A={amber:g}, R={red:g}; {direction}"


def burden(items: list[dict[str, Any]]) -> dict[str, Any]:
    weights = {"G": 0, "A": 1, "R": 2}
    verified = [item for item in items if item["status"] in weights]
    score = None if not verified else round(sum(weights[i["status"]] for i in verified) / (2 * len(verified)) * 100, 1)
    counts = {key: sum(i["status"] == key for i in items) for key in ("G", "A", "R", "B")}
    return {"score": score, "verified": len(verified), "total": len(items), "coverage": round(len(verified) / len(items) * 100, 1), "counts": counts}


def evaluate(config: dict[str, Any], fixture: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    results = []
    fixture = fixture or {}
    for item in config["indicators"]:
        if item.get("mode") != "automatic":
            obs = Observation(None, None, utc_now(), item["source"]["url"], False, "정성 지표: 자동 검증 규칙 미정의")
        elif item["id"] in fixture:
            raw = fixture[item["id"]]
            obs = Observation(raw.get("value"), raw.get("observed_at"), utc_now(), item["source"]["url"], raw.get("verified", True), raw.get("error"))
        else:
            obs = collect(item["source"])
        status, reason = classify(obs.value, item["rule"], obs.verified) if item.get("rule") else ("B", "검증 가능한 정량 규칙 없음")
        results.append({
            "id": item["id"], "axis": item["axis"], "title": item["title"], "status": status,
            "value": obs.value, "unit": item.get("unit"), "observed_at": obs.observed_at,
            "fetched_at": obs.fetched_at, "source_url": obs.source_url, "source_name": item["source"]["name"],
            "verified": obs.verified and status != "B", "reason": reason, "error": obs.error,
        })
    return results


def make_snapshot(config: dict[str, Any], items: list[dict[str, Any]], as_of: str) -> dict[str, Any]:
    macro = [i for i in items if i["axis"] == "macro"]
    ai = [i for i in items if i["axis"] == "ai"]
    return {
        "schema_version": 1,
        "kind": "live_observation",
        "as_of": as_of,
        "generated_at": utc_now(),
        "methodology": config["methodology"],
        "summary": {"overall": burden(items), "macro": burden(macro), "ai": burden(ai)},
        "items": items,
    }


def write_snapshot(root: Path, snapshot: dict[str, Any]) -> None:
    encoded = json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n"
    (root / "data" / "history").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "data" / "history").mkdir(parents=True, exist_ok=True)
    for path in (root / "data" / "latest.json", root / "docs" / "data" / "latest.json"):
        path.write_text(encoded, encoding="utf-8")
    for path in (root / "data" / "history" / f"{snapshot['as_of']}.json", root / "docs" / "data" / "history" / f"{snapshot['as_of']}.json"):
        path.write_text(encoded, encoding="utf-8")
    history = []
    for path in sorted((root / "data" / "history").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("kind") == "live_observation":
            history.append({"as_of": data["as_of"], "overall": data["summary"]["overall"]["score"], "macro": data["summary"]["macro"]["score"], "ai": data["summary"]["ai"]["score"], "coverage": data["summary"]["overall"]["coverage"]})
    (root / "docs" / "data" / "history.json").write_text(json.dumps(history, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


