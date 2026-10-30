"""Translate an airport-wide 07/25 forecast into the brief's runway movements."""

import math

from .domain import parse_time


def runway_plan(direction, rwy18_weather_state="unknown"):
    east = direction == "07"
    known = direction in ("07", "25")
    movement = ("eastbound" if east else "westbound") if known else None
    return {
        "landings": {"movement_direction": movement,
                     "heading_deg_true": (70 if east else 250) if known else None,
                     "approach_from": ("west" if east else "east") if known else None,
                     "runway_ends": (["07L", "07R"] if east else ["25R", "25L"]) if known else []},
        "centre_departures": {"movement_direction": movement,
                              "heading_deg_true": (70 if east else 250) if known else None,
                              "runway_end": ("07C" if east else "25C") if known else None},
        "runway18_departures": {"movement_direction": "southbound", "heading_deg_true": 180,
                                "runway_end": "18", "weather_state": rwy18_weather_state,
                                "official_operational_status": "unknown"},
        "individual_flight_assignment": None}


def prediction(weather, learned=None, basis="challenge_rules_raw_weather", wind_model=None):
    learned = learned or {}
    values = [learned.get(k) for k in ("p_od07", "p_od25")]
    valid_model = (learned.get("status") == "available" and learned.get("operating_direction") in ("07", "25")
                   and all(type(p) in (int, float) and math.isfinite(p) and 0 <= p <= 1 for p in values)
                   and abs(sum(values)-1) < 1e-6
                   and learned["operating_direction"] == ("07" if values[0] >= values[1] else "25"))
    direction = learned["operating_direction"] if valid_model else weather.get("operating_direction")
    if direction not in ("07", "25"):
        direction = None
    plan = runway_plan(direction, weather.get("rwy18_weather_state", "unknown"))
    return {"status": "available" if direction else "unavailable", "operating_direction": direction,
            "movement_direction": plan["landings"]["movement_direction"],
            "basis": "independently_trained_od_model" if valid_model else basis,
            "model_version": learned.get("model_version") if valid_model else None,
            "wind_model": wind_model,
            "p_od07": values[0] if valid_model else None, "p_od25": values[1] if valid_model else None,
            "certainty_score": max(values) if valid_model else None,
            "certainty_basis": "model_class_probability" if valid_model else "unavailable_without_validated_od_model",
            "probability_status": learned.get("probability_status") if valid_model else "not_available_for_weather_rule_prediction",
            "label_quality": learned.get("label_quality") if valid_model else None,
            "learned_model_status": learned.get("status", "unavailable"),
            "learned_model_reason": ("invalid_od_model_probabilities" if learned.get("status") == "available" else learned.get("reason")) if not valid_model else None,
            "runway_plan": plan}


def agreement(candidates, direction):
    # Corrections/blends share ICON-EU and must not become additional source votes.
    sources = {name: candidates.get(name, {}).get("operating_direction") for name in ("raw_icon_eu", "raw_gfs")}
    sources = {name: value for name, value in sources.items() if value in ("07", "25")}
    matches = sum(value == direction for value in sources.values()) if direction else 0
    return {"status": "available" if len(sources) == 2 and direction else "insufficient_sources",
            "sources": sources, "agreeing_sources": matches, "available_sources": len(sources),
            "fraction_supporting_prediction": matches/len(sources) if len(sources) == 2 and direction else None,
            "meaning": "Weather-model agreement, not the probability of actual operating direction."}


def outlook(points, next_change, observed=None):
    counts = {direction: sum(p["direction_forecast"]["operating_direction"] == direction for p in points)
              for direction in ("07", "25")}
    periods = []
    for point in points:
        forecast = point["direction_forecast"]
        direction = forecast["operating_direction"]
        previous = periods[-1] if periods else None
        if (previous and previous["operating_direction"] == direction
                and previous["basis"] == forecast["basis"]
                and (parse_time(point["valid_time"])-parse_time(previous["last_target"])).total_seconds() == 3600):
            previous.update(last_target=point["valid_time"], hours=previous["hours"]+1)
        else:
            periods.append({"first_target": point["valid_time"], "last_target": point["valid_time"], "hours": 1,
                            "operating_direction": direction, "movement_direction": forecast["movement_direction"],
                            "basis": forecast["basis"], "runway_plan": runway_plan(direction)})
    return {"status": "available" if sum(counts.values()) == len(points) and points else "partial" if sum(counts.values()) else "unavailable",
            "target": "airport_wide_07_25_direction", "hours_eastbound": counts["07"], "hours_westbound": counts["25"],
            "hours_unknown": len(points)-sum(counts.values()), "periods": periods, "next_change": next_change,
            "observed_operating_direction": (observed or {}).get("operating_direction"),
            "observed_at": (observed or {}).get("observed_at"),
            "limitations": ["Runway ends follow the challenge layout; individual flights are not assigned to a runway.",
                            "Weather-derived directions are not independently validated actual-OD predictions.",
                            "Periods group hourly targets; they do not exclude changes between samples.",
                            "Runway 18 remains southbound in both operating directions; weather suitability is not official status."]}


def enrich(snapshot):
    for point in snapshot["forecast"]:
        point["direction_forecast"] = prediction(point, point.get("operations_ml"), wind_model=point.get("model"))
    change = forecast_change(snapshot, snapshot.get("next_operating_direction_change"))
    snapshot["operating_direction_outlook"] = outlook(snapshot["forecast"], change, snapshot.get("observed_operations"))
    return snapshot


def enrich_comparison(snapshot):
    for point in snapshot["forecast"]:
        selected = point["selected"]
        forecast = prediction(selected, point.get("operations_ml"), "challenge_rules_selected_weather", selected.get("effective_candidate"))
        forecast["weather_model_agreement"] = agreement(point["candidates"], forecast["operating_direction"])
        point["direction_forecast"] = forecast
    change = forecast_change(snapshot, snapshot.get("next_rule_direction_change"))
    snapshot["operating_direction_outlook"] = outlook(snapshot["forecast"], change)
    return snapshot


def forecast_change(snapshot, weather_change):
    from .pipeline import next_change
    bases = {p["direction_forecast"]["basis"] for p in snapshot["forecast"]}
    if bases == {"independently_trained_od_model"}:
        return (snapshot.get("operations_model") or {}).get("next_change")
    if "independently_trained_od_model" not in bases:
        return weather_change
    points = [{"valid_time": p["valid_time"], "direction": p["direction_forecast"]["operating_direction"]} for p in snapshot["forecast"]]
    change = next_change(points, "direction", None)
    change["method"] = "mixed_learned_and_weather_hourly_sequence"
    return change
