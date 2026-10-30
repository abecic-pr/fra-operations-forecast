"""Official FRA departure-board records assessed against RWY18 weather only."""

from bisect import bisect_left
from datetime import datetime, timedelta
import json
from pathlib import Path
import time
from urllib.parse import urlencode

from .domain import UTC, iso, parse_time, runway_conditions
from .sources import SourceClient, write_json

BOARD_URL = "https://www.frankfurt-airport.com/en/_jcr_content.flights.json/filter"
BOARD_PAGE = "https://www.frankfurt-airport.com/en/flights-and-transfer/departures.html"
GROUND_TYPES = {"TRS", "BUS", "TRN", "TRAIN"}
FINISHED_STATUSES = {"departed", "off block", "off-block", "cancelled", "canceled"}


def optional_time(value):
    return iso(parse_time(value)) if value else None


def normalize_flight(raw, fetched_at, flighttype="departures"):
    if str(raw.get("ac", "")).upper() in GROUND_TYPES:
        return None, "ground_transport"
    finished = FINISHED_STATUSES | ({"arrived", "landed"} if flighttype == "arrivals" else set())
    if str(raw.get("status", "")).strip().lower() in finished:
        return None, "finished_or_cancelled"
    if not raw.get("id") or not raw.get("fnr") or not raw.get("sched"):
        return None, "missing_identity_or_schedule"
    try:
        scheduled = optional_time(raw["sched"])
        estimated = optional_time(raw.get("esti"))
        updated = optional_time(raw.get("lu"))
    except (ValueError, TypeError):
        return None, "invalid_timestamp"
    return {
        "flight_id": raw["id"], "flight_number": raw["fnr"],
        "codeshares": raw.get("cs", []), "airline": raw.get("alname"),
        "aircraft_type": raw.get("ac"), "destination_iata": raw.get("iata"),
        "destination": raw.get("apname"), "terminal": raw.get("terminal"),
        "gate": raw.get("gate"), "status": raw.get("status") or "unknown",
        "scheduled_departure_at": scheduled, "estimated_departure_at": estimated,
        "estimated_takeoff_at": None, "assigned_runway": None,
        "assessment_at": estimated or scheduled,
        "assessment_time_basis": "estimated_departure_proxy" if estimated else "scheduled_departure_proxy",
        "assessment_time_is_takeoff_estimate": False,
        "source": "frankfurt_airport_public_departure_board", "source_updated_at": updated,
        "fetched_at": fetched_at,
        "source_url": BOARD_PAGE,
    }, None


def fetch_departures(client, start, end, max_pages=60, progress=print, flighttype="departures"):
    # Catch delayed services whose original schedule is already in the past.
    query_start = start-timedelta(hours=6)
    records, issues, counts = {}, [], {}
    updated = None
    prior_pages = set()
    complete, reason = False, "page_limit"
    pages = 0
    for page in range(1,max_pages+1):
        params = {"perpage":50,"lang":"en","page":page,"flighttype":flighttype,"time":iso(query_start)}
        url = BOARD_URL + "?" + urlencode(params)
        try:
            response, meta = client.json("fra_departures",url)
            raw_rows = response.get("data")
            if not isinstance(raw_rows,list) or any(not isinstance(row,dict) for row in raw_rows):
                raise ValueError("Official board response has no flight data array")
        except (OSError,ValueError,TypeError) as exc:
            issues.append({"page":page,"error":str(exc)})
            reason = "source_error"
            break
        pages = page
        if response.get("luops"):
            try:
                updated = optional_time(response["luops"])
            except ValueError:
                pass
        if not raw_rows:
            complete,reason = True,"source_end"
            break
        signature = tuple(row.get("id") for row in raw_rows)
        if signature in prior_pages:
            reason = "repeated_page"
            issues.append({"page":page,"error":"Feed repeated a page; stopping to avoid an infinite pagination loop"})
            break
        prior_pages.add(signature)
        schedules = []
        for raw in raw_rows:
            try:
                if raw.get("sched"):
                    schedules.append(parse_time(raw["sched"]))
            except ValueError:
                pass
            flight, excluded = normalize_flight(raw,meta["fetched_at"],flighttype)
            if excluded:
                counts[excluded] = counts.get(excluded,0)+1
                continue
            at = parse_time(flight["assessment_at"])
            if not start <= at <= end:
                counts["outside_requested_window"] = counts.get("outside_requested_window",0)+1
                continue
            # Primary board records carry codeshares; do not create extra flights.
            records[flight["flight_id"]] = flight
        # The live feed's hasnext flag is false even when page 2 has results.
        # Stop using observed timestamps, empty pages and a bounded page limit.
        if schedules and max(schedules) >= end+timedelta(hours=1):
            complete,reason = True,"requested_horizon_reached"
            break
        if page % 10 == 0:
            progress(f"Departure board: {page} pages, {len(records)} upcoming flights.",flush=True)
        time.sleep(0.15)
    return sorted(records.values(),key=lambda f:(f["assessment_at"],f["flight_id"])), {
        "status":"available" if complete and not issues else "partial" if records else "unavailable",
        "url":BOARD_PAGE.replace("departures.html", "arrivals.html") if flighttype == "arrivals" else BOARD_PAGE,"feed_url":BOARD_URL,"source_updated_at":updated,
        "pages_fetched":pages,"coverage_complete":complete,"coverage_end_reason":reason,
        "requested_start":iso(start),"requested_end":iso(end),"schedule_lookback_hours":6,
        "excluded_records":counts,"errors":issues,
        "confirmed_runway_assignments_available":False,"estimated_takeoff_times_available":False,
        "pagination_consistency":"best_effort_live_board_may_change_during_pagination"}


def weather_sample(point):
    ml = point.get("ml", {})
    use_ml = ml.get("prediction_status") in ("ml_corrected", "raw_icon_eu_validation_fallback")
    weather = ml if use_ml else point
    components = weather.get("runway_wind",{}).get("18")
    if components is None:
        components = runway_conditions(weather)["18"]
    return {"valid_time":point["valid_time"],
            "wind_speed_kt":weather.get("wind_speed_kt"),
            "wind_from_deg_true":weather.get("wind_from_deg_true"),
            "wind_gust_kt":weather.get("wind_gust_kt"),
            "tailwind_kt":components.get("tailwind_kt"),
            "crosswind_kt":components.get("crosswind_kt"),
            "gust_crosswind_kt":components.get("gust_crosswind_kt"),
            "gust_direction_approximated":components.get("gust_direction_approximated",False),
            "weather_state":components.get("weather_state","unknown"),
            "p_weather_usable":ml.get("p_rwy18_weather_usable") if use_ml else None,
            "probability_status":ml.get("probability_status","unavailable") if use_ml else "unavailable_deterministic_baseline",
            "source_model":ml.get("source_model") if use_ml else point.get("model"),
            "model_run_at":weather.get("model_run_at"),
            "prediction_status":ml.get("prediction_status") if use_ml else "challenge_rules_baseline"}


class Runway18Weather:
    def __init__(self, snapshot, now):
        self.snapshot = snapshot or {}
        self.points = sorted(self.snapshot.get("forecast",[]),key=lambda r:r["valid_time"])
        self.times = [parse_time(r["valid_time"]) for r in self.points]
        generated = self.snapshot.get("generated_at")
        self.age = max(0,(now-parse_time(generated)).total_seconds()) if generated else None

    def assess(self, at):
        result = {"runway":"18","takeoff_direction":"south","heading_deg_true":180,
                  "assignment_status":"unknown","p_departure_from_rwy18":None,
                  "weather_state":"unknown","p_weather_usable":None,
                  "sample_probability_range":None,"forecast_samples":[],
                  "time_alignment":"forecast_unavailable","scope":"weather_at_forecast_samples_only",
                  "forecast_generated_at":self.snapshot.get("generated_at"),
                  "forecast_age_seconds":self.age,
                  "data_status":"unavailable" if self.age is None else "stale" if self.age > 7200 else "recent"}
        if not self.times:
            return result
        i = bisect_left(self.times,at)
        if i < len(self.times) and self.times[i] == at:
            selected,alignment = [self.points[i]],"exact_hour"
        elif 0 < i < len(self.times) and self.times[i]-self.times[i-1] <= timedelta(hours=1):
            selected,alignment = [self.points[i-1],self.points[i]],"bracketing_hours"
        elif i == 0 and self.times[0]-at <= timedelta(hours=1):
            selected,alignment = [self.points[0]],"next_hour_proxy"
        else:
            result["time_alignment"] = "outside_forecast_horizon" if i == len(self.times) or i == 0 else "forecast_gap"
            return result
        samples = [weather_sample(point) for point in selected]
        states = {r["weather_state"] for r in samples}
        chance = [r["p_weather_usable"] for r in samples]
        result.update(time_alignment=alignment,forecast_samples=samples,
                      weather_state=next(iter(states)) if len(states)==1 else "unknown" if "unknown" in states else "changing")
        if all(p is not None for p in chance):
            result["sample_probability_range"]={"min":min(chance),"max":max(chance)}
            # Do not interpolate hourly probabilities or call a gate time takeoff.
            if alignment == "exact_hour":
                result["p_weather_usable"]=chance[0]
        return result


def build_departure_snapshot(flights, source, forecast_snapshot, now):
    weather = Runway18Weather(forecast_snapshot,now)
    enriched = [{**flight,"runway18":weather.assess(parse_time(flight["assessment_at"]))} for flight in flights]
    return {"schema_version":"1.0","airport_icao":"EDDF","runway":"18",
            "generated_at":iso(now),"display_timezone":"Europe/Berlin",
            "scope":"upcoming_FRA_flights_assessed_for_RWY18_weather_not_confirmed_assignments",
            "source":source,"flight_count":len(enriched),"departures":enriched,
            "limitations":["The public board does not provide assigned runways or estimated wheels-off times.",
                           "Published estimated/scheduled departure times are assessment proxies; no taxi delay is invented.",
                           "These are FRA flights assessed for RWY18 weather, not a list of confirmed RWY18 departures.",
                           "Runway 18 takeoffs are southbound. Individual runway-use probability remains unavailable.",
                           "Hourly probability samples are not interpolated; their min/max is not an interval-use probability.",
                           "Weather probability estimates are provisional and separate from official runway availability.",
                           "The public passenger board may omit cargo, private services, and delays originating more than six hours earlier."]}


def refresh_departures(data_dir="data", hours=48, forecast_snapshot=None, progress=print):
    if not 1 <= hours <= 48:
        raise ValueError("Departure horizon must be between 1 and 48 hours")
    root = Path(data_dir)
    root.mkdir(parents=True,exist_ok=True)
    now = datetime.now(UTC)
    if forecast_snapshot is None:
        try:
            forecast_snapshot=json.loads((root/"forecast.json").read_text())
        except (OSError,ValueError):
            forecast_snapshot={}
    client = SourceClient(root,timeout=20)
    progress("Fetching the official FRA departure board for RWY18 weather assessments…",flush=True)
    flights, source = fetch_departures(client,now,now+timedelta(hours=hours),progress=progress)
    result=build_departure_snapshot(flights,source,forecast_snapshot,datetime.now(UTC))
    write_json(root/"runway18-departures.json",result)
    write_json(root/"runway18-departures-sources.json",client.checks)
    progress(f"Saved {len(flights)} upcoming flights with RWY18 weather assessments ({source['status']}).",flush=True)
    return result
