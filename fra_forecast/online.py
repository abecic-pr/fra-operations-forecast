"""Hourly online learning from our own forecast errors.

Each refresh (1) scores forecasts we archived earlier against DWD 01420
measurements that have since arrived, (2) updates a time-decayed ridge
regression per weather model and lead-time bucket with those errors, and
(3) publishes the learned correction for the new 48-hour forecast.

Scores use the value that was published before the measurement existed
(test-then-train), so every reported number is out-of-sample. This is
supervised online learning, not reinforcement learning: there is no action
or reward, only forecast error. Pure standard library on purpose: the live
pipeline must run without the optional ML dependencies.
"""
from collections import Counter
from datetime import datetime, timedelta
import json
import math
from pathlib import Path

from .domain import UTC, iso, number, parse_time, runway_conditions
from .ml_data import observation_target, uv
from .sources import write_json

MODEL_VERSION = "online-v1"
# Chosen on the 2026-05-07..09-02 ICON-EU replay only (tau 72-720 h, prior 6-72, +/- diurnal).
TAU_HOURS = 720.0  # error memory half-life ~ 21 days
PRIOR = 24.0  # pull toward the raw forecast, in verified-hour equivalents
BUCKETS = ((1, 3), (4, 6), (7, 12), (13, 24), (25, 48))
CHALLENGE_LEADS = (1, 6, 24)
GUARD = {"wind": 15.0, "temperature": 8.0}  # larger corrections fall back to raw
TEST_WINDOW = ("2026-09-21", "2026-10-27")  # same chronological test issues as the wind model


def bucket(lead):
    lead = max(1, math.ceil(lead))
    return next((f"{lo}-{hi}" for lo, hi in BUCKETS if lead <= hi), f"{BUCKETS[-1][0]}-{BUCKETS[-1][1]}")


def features(raw, valid_time):
    angle = 2 * math.pi * parse_time(valid_time).hour / 24
    return [1.0, *raw, math.sin(angle), math.cos(angle)]


def solve(A, B):
    """Gauss-Jordan for the small symmetric positive-definite systems below."""
    n = len(A)
    M = [list(A[i]) + list(B[i]) for i in range(n)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(M[r][c]))
        M[c], M[p] = M[p], M[c]
        M[c] = [v / M[c][c] for v in M[c]]
        for r in range(n):
            if r != c and M[r][c]:
                f = M[r][c]
                M[r] = [a - f * b for a, b in zip(M[r], M[c])]
    return [row[n:] for row in M]


class Learner:
    """Weighted ridge y = x W per (model, kind, bucket), shrunk to W = identity (the raw forecast)."""

    def __init__(self, state=None):
        state = state or {}
        self.cells = state.get("cells", {})
        self.clock = state.get("clock")
        self._weights = {}

    def predict(self, model, kind, lead, valid_time, raw):
        x = features(raw, valid_time)
        n, m = len(x), len(raw)
        key = f"{model}|{kind}|{bucket(lead)}"
        if key not in self._weights:
            cell = self.cells.get(key) or {"A": [[0.0] * n for _ in range(n)], "B": [[0.0] * m for _ in range(n)]}
            A = [[cell["A"][i][j] + (PRIOR if i == j else 0.0) for j in range(n)] for i in range(n)]
            B = [[cell["B"][i][j] + (PRIOR if i == j + 1 else 0.0) for j in range(m)] for i in range(n)]
            self._weights[key] = solve(A, B)
        W = self._weights[key]
        return [sum(x[i] * W[i][j] for i in range(n)) for j in range(m)], (self.cells.get(key) or {}).get("weight", 0.0)

    def update(self, samples):
        if not samples:
            return
        latest = max(parse_time(s["valid_time"]) for s in samples)
        if self.clock:
            hours = max(0.0, (latest - parse_time(self.clock)).total_seconds() / 3600)
            decay = math.exp(-hours / TAU_HOURS)
            for cell in self.cells.values():
                cell["A"] = [[v * decay for v in row] for row in cell["A"]]
                cell["B"] = [[v * decay for v in row] for row in cell["B"]]
                cell["weight"] *= decay
            latest = max(latest, parse_time(self.clock))
        self.clock = iso(latest)
        # Each verified hour counts once per bucket, however many issues forecast it.
        keys = [f"{s['model']}|{s['kind']}|{bucket(s['lead'])}" for s in samples]
        counts = Counter(zip(keys, (s["valid_time"] for s in samples)))
        for key, s in zip(keys, samples):
            x, y = features(s["raw"], s["valid_time"]), s["actual"]
            cell = self.cells.setdefault(key, {"A": [[0.0] * len(x) for _ in x], "B": [[0.0] * len(y) for _ in x], "weight": 0.0})
            w = 1.0 / counts[(key, s["valid_time"])]
            for i in range(len(x)):
                for j in range(len(x)):
                    cell["A"][i][j] += w * x[i] * x[j]
                for j in range(len(y)):
                    cell["B"][i][j] += w * x[i] * y[j]
            cell["weight"] += w
        self._weights = {}

    def state(self):
        return {"cells": self.cells, "clock": self.clock}


def correct(learner, model, lead, valid_time, u, v, temperature):
    """Learned (u, v, t) plus status; guarded fall-back to raw on implausible jumps."""
    result = {"u": u, "v": v, "t": temperature, "weight": 0.0, "guarded": False}
    if u is not None and v is not None:
        (lu, lv), weight = learner.predict(model, "wind", lead, valid_time, (u, v))
        if math.hypot(lu - u, lv - v) <= GUARD["wind"]:
            result.update(u=lu, v=lv, weight=weight)
        else:
            result["guarded"] = True
    if temperature is not None:
        (lt,), _ = learner.predict(model, "temperature", lead, valid_time, (temperature,))
        if abs(lt - temperature) <= GUARD["temperature"]:
            result["t"] = lt
        else:
            result["guarded"] = True
    return result


def speed_direction(u, v):
    if u is None or v is None:
        return None, None
    speed = math.hypot(u, v)
    return speed, (math.degrees(math.atan2(-u, -v)) % 360 if speed >= 0.5 else None)


def scores(rows):
    """Raw vs learned error for rows holding raw/learned/actual u, v, t."""
    result = {"samples": len(rows)}
    for name in ("raw", "learned"):
        wind = [r for r in rows if r[name]["u"] is not None and r["actual"]["u"] is not None]
        temps = [r for r in rows if r[name]["t"] is not None and r["actual"]["t"] is not None]
        directions = []
        for r in wind:
            _, predicted = speed_direction(r[name]["u"], r[name]["v"])
            actual_speed, actual = speed_direction(r["actual"]["u"], r["actual"]["v"])
            if predicted is not None and actual is not None and actual_speed >= 3:  # calm exclusion as in wind_ml
                directions.append(abs((predicted - actual + 180) % 360 - 180))
        result[name] = {
            "vector_rmse_kt": math.sqrt(sum((r[name]["u"] - r["actual"]["u"]) ** 2 + (r[name]["v"] - r["actual"]["v"]) ** 2 for r in wind) / len(wind)) if wind else None,
            "speed_mae_kt": sum(abs(speed_direction(r[name]["u"], r[name]["v"])[0] - speed_direction(r["actual"]["u"], r["actual"]["v"])[0]) for r in wind) / len(wind) if wind else None,
            "direction_mae_deg": sum(directions) / len(directions) if directions else None,
            "temperature_mae_c": sum(abs(r[name]["t"] - r["actual"]["t"]) for r in temps) / len(temps) if temps else None,
            "wind_samples": len(wind), "temperature_samples": len(temps)}
    raw, learned = result["raw"]["vector_rmse_kt"], result["learned"]["vector_rmse_kt"]
    result["wind_error_reduction"] = 1 - learned / raw if raw and learned is not None else None
    raw, learned = result["raw"]["temperature_mae_c"], result["learned"]["temperature_mae_c"]
    result["temperature_error_reduction"] = 1 - learned / raw if raw and learned is not None else None
    return result


def by_lead(rows):
    return {"all_leads": scores(rows), **{f"{lead}h": scores([r for r in rows if r["lead"] == lead]) for lead in CHALLENGE_LEADS}}


def replay(samples):
    """Chronological test-then-train over issued forecasts; returns the learner and scored rows."""
    learner, pending, scored = Learner(), [], []
    events = sorted([(s["available_at"], 0, i) for i, s in enumerate(samples)] +
                    [(s["issued_at"], 1, i) for i, s in enumerate(samples)])
    for _, kind, i in events:
        s = samples[i]
        if kind == 0:
            pending.append(s)
            continue
        if pending:
            learner.update([sample for p in pending for sample in to_updates(p)])
            pending = []
        learned = correct(learner, s["model"], s["lead"], s["valid_time"], s["raw"]["u"], s["raw"]["v"], s["raw"]["t"])
        scored.append({**s, "learned": {k: learned[k] for k in ("u", "v", "t")}})
    return learner, scored


def to_updates(row):
    out = []
    base = {"model": row["model"], "lead": row["lead"], "valid_time": row["valid_time"]}
    if None not in (row["raw"]["u"], row["raw"]["v"], row["actual"]["u"], row["actual"]["v"]):
        out.append({**base, "kind": "wind", "raw": (row["raw"]["u"], row["raw"]["v"]), "actual": (row["actual"]["u"], row["actual"]["v"])})
    if row["raw"]["t"] is not None and row["actual"]["t"] is not None:
        out.append({**base, "kind": "temperature", "raw": (row["raw"]["t"],), "actual": (row["actual"]["t"],)})
    return out


def load_state(folder):
    path = Path(folder) / "state.json"
    try:
        state = json.loads(path.read_text())
        return state if state.get("model_version") == MODEL_VERSION else {}
    except (OSError, ValueError):
        return {}


def step(root, snapshot, observations, temperatures, now=None):
    """Verify matured forecasts, learn from their errors, then correct and archive this issue."""
    now = now or datetime.now(UTC)
    folder = Path(root) / "online"
    state = load_state(folder)
    learner = Learner(state)
    index = {r["valid_time"]: r for r in observations}
    verified, waiting = [], []
    for p in state.get("pending", []):
        at = parse_time(p["valid_time"])
        target = observation_target(index, at) if at <= now else None
        if target is None:
            if now - at < timedelta(hours=12):
                waiting.append(p)
            continue  # never verified: no measurement arrived within 12 h
        verified.append({**p, "actual": {"u": target["target_u_kt"], "v": target["target_v_kt"],
                                         "t": number(temperatures.get(p["valid_time"]))},
                         "verified_at": iso(now)})
    learner.update([sample for row in verified for sample in to_updates(row)])
    log = (state.get("verified", []) + [r for r in verified if r["lead"] in CHALLENGE_LEADS])
    log = [r for r in log if now - parse_time(r["valid_time"]) <= timedelta(days=7)]
    totals = state.get("totals", {"samples": 0, "raw_sq": 0.0, "learned_sq": 0.0})
    for row in verified:
        if None not in (row["raw"]["u"], row["actual"]["u"]):
            totals["samples"] += 1
            totals["raw_sq"] += (row["raw"]["u"] - row["actual"]["u"]) ** 2 + (row["raw"]["v"] - row["actual"]["v"]) ** 2
            totals["learned_sq"] += (row["learned"]["u"] - row["actual"]["u"]) ** 2 + (row["learned"]["v"] - row["actual"]["v"]) ** 2

    issue_hour = iso(now.replace(minute=0, second=0, microsecond=0))
    archive = state.get("last_issue_hour") != issue_hour
    weights = []
    for point in snapshot.get("forecast", []):
        components = uv(point.get("wind_speed_kt"), point.get("wind_from_deg_true"))
        u, v = components if components else (None, None)
        raw_t = number(point.get("temperature_c"))
        model, lead = point.get("model"), max(1, math.ceil(point.get("lead_time_hours") or 1))
        if model is None or (u is None and raw_t is None):
            point["online"] = {"status": "unavailable_missing_forecast", "model_version": MODEL_VERSION}
            continue
        learned = correct(learner, model, lead, point["valid_time"], u, v, raw_t)
        weights.append(learned["weight"])
        speed, direction = speed_direction(learned["u"], learned["v"])
        weather = {"wind_speed_kt": speed, "wind_from_deg_true": direction, "wind_gust_kt": point.get("wind_gust_kt")}
        point["online"] = {**weather, "temperature_c": learned["t"],
                           "raw_wind_speed_kt": point.get("wind_speed_kt"), "raw_wind_from_deg_true": point.get("wind_from_deg_true"),
                           "raw_temperature_c": raw_t, "source_model": model, "lead_bucket_hours": bucket(lead),
                           "training_weight_hours": round(learned["weight"], 2), "model_version": MODEL_VERSION,
                           "status": "raw_forecast_guarded" if learned["guarded"] else "learned_correction" if learned["weight"] > 0 else "cold_start_raw_forecast",
                           "runway_wind": runway_conditions(weather) if speed is not None else None}
        if archive:
            waiting.append({"issued_at": iso(now), "valid_time": point["valid_time"], "lead": lead, "model": model,
                            "raw": {"u": u, "v": v, "t": raw_t},
                            "learned": {k: learned[k] for k in ("u", "v", "t")}})
    state = {"model_version": MODEL_VERSION, **learner.state(), "pending": waiting, "verified": log, "totals": totals,
             "last_issue_hour": issue_hour if archive else state.get("last_issue_hour"),
             "first_live_update": state.get("first_live_update") or (iso(now) if verified else None),
             "backtest": state.get("backtest")}
    write_json(folder / "state.json", state)
    report = live_report(state, now)
    write_json(folder / "report.json", report)
    snapshot["online_learning"] = {"status": "learning" if any(weights) else "cold_start",
                                   "model_version": MODEL_VERSION, "updated_at": iso(now),
                                   "verified_this_refresh": len(verified), "pending_forecasts": len(waiting),
                                   "report_url": "/api/online-learning",
                                   "limitations": report["limitations"]}
    return report


def display(row):
    out = {"valid_time": row["valid_time"], "issued_at": row["issued_at"], "lead_hours": row["lead"], "model": row["model"]}
    for name in ("raw", "learned", "actual"):
        speed, direction = speed_direction(row[name]["u"], row[name]["v"])
        out[name] = {"wind_speed_kt": speed, "wind_from_deg_true": direction, "temperature_c": row[name]["t"]}
    return out


def live_report(state, now):
    log = state.get("verified", [])
    totals = state.get("totals", {})
    n = totals.get("samples", 0)
    return {"schema_version": "1.0", "model_version": MODEL_VERSION, "updated_at": iso(now),
            "method": "Hourly test-then-train: score each archived forecast against DWD 01420, then update a "
                      "time-decayed ridge regression (wind u/v and 2 m temperature) per weather model and lead bucket.",
            "hyperparameters": {"memory_tau_hours": TAU_HOURS, "prior_strength_hours": PRIOR,
                                "lead_buckets_hours": [f"{lo}-{hi}" for lo, hi in BUCKETS],
                                "features": ["raw forecast", "UTC hour sin/cos", "intercept"],
                                "selection": "ICON-EU replay, issues 2026-05-07 to 2026-09-02 only"},
            "live": {"first_update": state.get("first_live_update"), "pending_forecasts": len(state.get("pending", [])),
                     "verified_forecasts_all_leads": n,
                     "vector_rmse_kt_all_leads": {"raw": math.sqrt(totals["raw_sq"] / n), "learned": math.sqrt(totals["learned_sq"] / n)} if n else None,
                     "last_7_days": by_lead(log)},
            "recent": [display(r) for r in sorted(log, key=lambda r: r["valid_time"]) if r["lead"] == 1][-24:],
            "backtest": state.get("backtest"),
            "limitations": ["Supervised online learning from forecast error; not reinforcement learning.",
                            "Truth is provisional DWD 01420 10-minute data (QN 2/3), not final quality-controlled values.",
                            "Gusts are not corrected; runway components use the learned mean wind with the raw gust.",
                            "Operating direction and RWY18 outputs still use the raw forecast; the learned wind is published alongside."]}


def train(root, days=30, progress=print):
    """Warm the learner by replaying archived forecasts hour by hour, and score it out-of-sample."""
    from .ml_data import build_rows
    from .sources import LIVE_FIELDS, SourceClient, dwd_observations, dwd_temperature, forecast

    root = Path(root)
    samples = []
    eu_path = root / "ml" / "dataset.json"
    if eu_path.exists():
        for r in json.loads(eu_path.read_text())["rows"]:
            samples.append(sample(r, "icon_eu", None, None))
        progress(f"ICON-EU replay rows: {len(samples)}", flush=True)
    client = SourceClient(root)
    now = datetime.now(UTC)
    first = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days)
    observations = dwd_observations(client, first - timedelta(hours=1), now)
    temperatures = dwd_temperature(client, first, now, kinds=(("recent", "akt"), ("now", "now")))
    runs = []
    run_times = [first + timedelta(hours=h) for h in range(0, days * 24, 6) if first + timedelta(hours=h + 6) < now]
    for at in run_times:
        try:
            runs.append({"run_at": iso(at), **forecast(client, "icon_d2", at, forecast_days=2, fields=LIVE_FIELDS)})
        except (OSError, ValueError, KeyError) as exc:
            progress(f"  ICON-D2 {iso(at)} unavailable: {exc}", flush=True)
    raw_t = {(run["run_at"], r["valid_time"]): r.get("temperature_c") for run in runs for r in run["hourly"]}
    d2 = [sample(r, "icon_d2", raw_t.get((r["model_run_at"], r["valid_time"])), temperatures.get(r["valid_time"]))
          for r in build_rows(runs, observations)]
    progress(f"ICON-D2 replay rows: {len(d2)} from {len(runs)}/{len(run_times)} runs", flush=True)
    samples += d2
    if not samples:
        raise ValueError("No archived forecasts with matching DWD measurements to replay")
    learner, scored = replay(samples)
    eu = [r for r in scored if r["model"] == "icon_eu"]
    backtest = {"generated_at": iso(now), "model_version": MODEL_VERSION, "protocol":
                "Chronological replay: each forecast is corrected only with errors measured before its issue "
                "time (ICON +4 h publication, DWD +1 h assumed), then scored, then learned from.",
                "icon_eu_test": {"issues": f"{TEST_WINDOW[0]} to {TEST_WINDOW[1]} (excl.)",
                                 **by_lead([r for r in eu if TEST_WINDOW[0] <= r["issued_at"] < TEST_WINDOW[1]])},
                "icon_eu_development": by_lead([r for r in eu if r["issued_at"] < "2026-09-03"]),
                "icon_d2_recent": {"issues": f"last {days} days", **by_lead([r for r in scored if r["model"] == "icon_d2"])},
                "limitations": ["Historical publication times are assumed, as in the wind model.",
                                "Retrospective DWD values may include later corrections.",
                                "ICON-D2 replay uses 00/06/12/18 UTC runs; live issues are hourly."]}
    folder = root / "online"
    write_json(folder / "backtest.json", backtest)
    state = load_state(folder)
    summary = {k: backtest[k] for k in ("generated_at", "protocol")}
    summary.update({k: {lead: backtest[k][lead] for lead in ("issues", "1h", "6h", "24h", "all_leads")} for k in ("icon_eu_test", "icon_d2_recent")})
    state.update({"model_version": MODEL_VERSION, **learner.state(), "backtest": summary})
    write_json(folder / "state.json", state)
    write_json(folder / "report.json", live_report(state, now))
    return {"samples": len(samples), **backtest}


def sample(row, model, raw_t, actual_t):
    return {"issued_at": row["decision_time"], "valid_time": row["valid_time"],
            "available_at": iso(parse_time(row["valid_time"]) + timedelta(hours=1)),
            "lead": row["lead_time_hours"], "model": model,
            "raw": {"u": row["raw_u_kt"], "v": row["raw_v_kt"], "t": raw_t},
            "actual": {"u": row["target_u_kt"], "v": row["target_v_kt"], "t": actual_t}}
