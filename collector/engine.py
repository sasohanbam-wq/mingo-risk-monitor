from __future__ import annotations

import csv
import io
import json
import math
import statistics
import urllib.request
import urllib.parse
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any


USER_AGENT = "mingo-risk-monitor/1.0 https://github.com/sasohanbam-wq/mingo-risk-monitor"


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


@lru_cache(maxsize=128)
def fetch_text(url: str, timeout: int = 20) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8")


def fred_rows(series: str) -> list[tuple[str, float]]:
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"
    rows = list(csv.DictReader(io.StringIO(fetch_text(url))))
    result = []
    for row in rows:
        raw = row.get(series)
        if raw not in (None, "", "."):
            result.append((row.get("DATE", row.get("observation_date", "")), float(raw)))
    if not result:
        raise ValueError(f"no numeric observations for {series}")
    return result


def fred_value(source: dict[str, Any]) -> tuple[float, str]:
    rows = fred_rows(source["series"])
    transform = source.get("transform", "latest")
    periods = int(source.get("periods", 1))
    if transform == "latest":
        return rows[-1][1], rows[-1][0]
    if transform == "pct_change":
        if len(rows) <= periods:
            raise ValueError("insufficient history for percent change")
        return (rows[-1][1] / rows[-1 - periods][1] - 1) * 100, rows[-1][0]
    if transform == "delta":
        if len(rows) <= periods:
            raise ValueError("insufficient history for delta")
        return rows[-1][1] - rows[-1 - periods][1], rows[-1][0]
    other = fred_rows(source["secondary_series"])
    if transform == "spread":
        scale = float(source.get("scale", 1))
        return (rows[-1][1] - other[-1][1]) * scale, min(rows[-1][0], other[-1][0])
    if transform == "correlation":
        by_date_a = dict(rows)
        by_date_b = dict(other)
        common = sorted(set(by_date_a) & set(by_date_b))[-int(source.get("window", 60)) - 1:]
        if len(common) < 20:
            raise ValueError("insufficient aligned observations")
        a = [by_date_a[d] for d in common]
        b = [by_date_b[d] for d in common]
        ar = [(a[i] / a[i - 1] - 1) * 100 for i in range(1, len(a))]
        bd = [b[i] - b[i - 1] for i in range(1, len(b))]
        return statistics.correlation(ar, bd), common[-1]
    raise ValueError(f"unsupported FRED transform: {transform}")


def annual_facts(companyfacts: dict[str, Any], concepts: list[str]) -> list[dict[str, Any]]:
    facts = companyfacts.get("facts", {}).get("us-gaap", {})
    candidates = []
    for concept in concepts:
        for fact in facts.get(concept, {}).get("units", {}).get("USD", []):
            if fact.get("form") == "10-K" and fact.get("fp") == "FY" and isinstance(fact.get("val"), (int, float)):
                start, end = fact.get("start"), fact.get("end")
                if start and end:
                    candidates.append(fact)
    dedup: dict[tuple[str, str], dict[str, Any]] = {}
    for fact in candidates:
        key = (fact["start"], fact["end"])
        if key not in dedup or fact.get("filed", "") > dedup[key].get("filed", ""):
            dedup[key] = fact
    return sorted(dedup.values(), key=lambda x: (x["end"], x.get("filed", "")))


def instant_facts(companyfacts: dict[str, Any], concepts: list[str]) -> list[dict[str, Any]]:
    facts = companyfacts.get("facts", {}).get("us-gaap", {})
    candidates = []
    for concept in concepts:
        for fact in facts.get(concept, {}).get("units", {}).get("USD", []):
            if fact.get("form") in ("10-Q", "10-K") and isinstance(fact.get("val"), (int, float)) and fact.get("end"):
                candidates.append(fact)
    dedup: dict[str, dict[str, Any]] = {}
    for fact in candidates:
        end = fact["end"]
        if end not in dedup or fact.get("filed", "") > dedup[end].get("filed", ""):
            dedup[end] = fact
    return sorted(dedup.values(), key=lambda x: (x["end"], x.get("filed", "")))


def sec_formula_value(source: dict[str, Any]) -> tuple[float, str]:
    numerator = source["numerator"]
    denominator = source["denominator"]
    numerator_period = source.get("numerator_period", source.get("period", "annual"))
    denominator_period = source.get("denominator_period", source.get("period", "annual"))
    total_num = total_den = 0.0
    observed = []
    used = 0
    for cik in source["ciks"]:
        payload = json.loads(fetch_text(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{int(cik):010d}.json"))
        get_num = annual_facts if numerator_period == "annual" else instant_facts
        get_den = annual_facts if denominator_period == "annual" else instant_facts
        nums, dens = get_num(payload, numerator), get_den(payload, denominator)
        if not nums or not dens:
            continue
        num, den = nums[-1], dens[-1]
        if den["val"] == 0:
            continue
        total_num += float(num["val"])
        total_den += float(den["val"])
        observed.append(min(num["end"], den["end"]))
        used += 1
    minimum = int(source.get("minimum_companies", len(source["ciks"])))
    if used < minimum or total_den == 0:
        raise ValueError(f"only {used}/{len(source['ciks'])} companies had comparable facts")
    return total_num / total_den * float(source.get("scale", 100)), min(observed)


def sec_efts_count(source: dict[str, Any]) -> tuple[float, str]:
    today = datetime.now(timezone.utc).date()
    start = today.fromordinal(today.toordinal() - int(source.get("days", 90)))
    params = urllib.parse.urlencode({
        "q": source["query"], "forms": source.get("forms", "S-1,S-1/A"),
        "startdt": start.isoformat(), "enddt": today.isoformat(), "from": 0, "size": 1,
    })
    payload = json.loads(fetch_text(f"https://efts.sec.gov/LATEST/search-index?{params}"))
    total = payload.get("hits", {}).get("total", {})
    value = total.get("value") if isinstance(total, dict) else total
    if not isinstance(value, (int, float)):
        raise ValueError("SEC EFTS total missing")
    return float(value), today.isoformat()


def collect(source: dict[str, Any]) -> Observation:
    fetched_at = utc_now()
    url = source["url"]
    try:
        if source["type"] in ("fred_csv", "fred"):
            value, observed_at = fred_value(source)
            return Observation(value, observed_at, fetched_at, url, True)
        if source["type"] == "sec_formula":
            value, observed_at = sec_formula_value(source)
            return Observation(value, observed_at, fetched_at, url, True)
        if source["type"] == "sec_efts_count":
            value, observed_at = sec_efts_count(source)
            return Observation(value, observed_at, fetched_at, url, True)
        body = fetch_text(url)
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
            "proxy": item.get("proxy"), "limitation": item.get("limitation"),
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

