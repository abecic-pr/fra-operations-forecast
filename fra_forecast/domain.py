"""Challenge rules. Wind directions are FROM true north; speeds are knots."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import math

UTC = timezone.utc
RULESET = {
    "version": "fraalliance-2026-v1",
    "landing_tailwind_limit_kt": 10.0,
    "departure_tailwind_limit_kt": 15.0,
    "crosswind_limit_kt": 40.0,
    "tailwind_persistence_minutes": 30,
    "runway_headings_true": {"07": 70.0, "25": 250.0, "18": 180.0},
}


def parse_time(value):
    result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError(f"Timestamp needs an explicit timezone: {value}")
    return result.astimezone(UTC)


def iso(value):
    return value.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def number(value):
    try:
        result = float(value)
        return result if math.isfinite(result) and result != -999 else None
    except (ValueError, TypeError):
        return None


def wind_components(speed, direction, heading):
    speed, direction = number(speed), number(direction)
    if speed is None or speed < 0:
        return None
    if speed == 0:
        return {"headwind_kt": 0.0, "tailwind_kt": 0.0, "crosswind_kt": 0.0}
    if direction is None or not 0 <= direction <= 360:
        return None
    delta = math.radians(direction - heading)
    head = speed * math.cos(delta)
    return {"headwind_kt": head, "tailwind_kt": max(0.0, -head),
            "crosswind_kt": abs(speed * math.sin(delta))}


def runway_conditions(weather):
    results = {}
    for runway, heading in RULESET["runway_headings_true"].items():
        mean = wind_components(weather.get("wind_speed_kt"), weather.get("wind_from_deg_true"), heading)
        gust_direction = weather.get("gust_from_deg_true")
        approximate = gust_direction is None
        if approximate:
            gust_direction = weather.get("wind_from_deg_true")
        gust = wind_components(weather.get("wind_gust_kt"), gust_direction, heading)
        limit = 15.0 if runway == "18" else 10.0
        cross = max(mean["crosswind_kt"], gust["crosswind_kt"]) if mean and gust else None
        reasons = []
        if mean and mean["tailwind_kt"] >= limit:
            reasons.append("tailwind_limit_reached")
        if (mean and mean["crosswind_kt"] > 40) or (gust and gust["crosswind_kt"] > 40):
            reasons.append("crosswind_limit_exceeded")
        if reasons:
            state = "not_usable"
        elif mean is None or gust is None:
            state = "unknown"
            reasons.append("missing_wind_or_gust")
        else:
            state = "usable"
        results[runway] = {
            "heading_deg_true": heading, **(mean or {"headwind_kt": None, "tailwind_kt": None, "crosswind_kt": None}),
            "gust_crosswind_kt": gust["crosswind_kt"] if gust else None,
            "gust_direction_approximated": bool(gust and approximate),
            "tailwind_margin_kt": limit - mean["tailwind_kt"] if mean else None,
            "crosswind_margin_kt": 40 - cross if cross is not None else None,
            "weather_state": state, "reason_codes": reasons,
        }
    return results


@dataclass
class DirectionState:
    direction: str | None = None
    tailwind_since: datetime | None = None
    previous_time: datetime | None = None

    def step(self, weather, resolution_minutes=15):
        at = parse_time(weather["valid_time"])
        conditions = runway_conditions(weather)
        reasons = []
        if self.previous_time and at <= self.previous_time:
            raise ValueError("Baseline steps must be strictly increasing")
        if self.previous_time and at - self.previous_time > timedelta(minutes=resolution_minutes * 1.5):
            self.tailwind_since = None
            reasons.append("gap_resets_persistence")
        self.previous_time = at
        if conditions["07"]["headwind_kt"] is None:
            self.tailwind_since = None
            return self._output(None, conditions, reasons + ["wind_direction_unavailable"])
        if "crosswind_limit_exceeded" in conditions["07"]["reason_codes"]:
            self.tailwind_since = None
            return self._output(None, conditions, reasons + ["parallel_runways_crosswind_limited"])
        if self.direction not in ("07", "25"):
            self.direction = "07" if conditions["07"]["headwind_kt"] >= 0 else "25"
            reasons.append("initialized_from_wind_not_observed_operations")
        tailwind = conditions[self.direction]["tailwind_kt"]
        if tailwind >= 10:
            self.direction = "25" if self.direction == "07" else "07"
            self.tailwind_since = None
            reasons.append("landing_tailwind_limit_reached")
        elif tailwind > 1e-9:
            if self.tailwind_since is None:
                self.tailwind_since = at
            if at - self.tailwind_since > timedelta(minutes=30):
                self.direction = "25" if self.direction == "07" else "07"
                self.tailwind_since = None
                reasons.append("tailwind_persisted_over_30_minutes")
            else:
                reasons.append("holding_direction_with_short_tailwind")
        else:
            self.tailwind_since = None
            reasons.append("headwind_or_calm")
        return self._output(self.direction, conditions, reasons)

    @staticmethod
    def _output(direction, conditions, reasons):
        return {"operating_direction": direction,
                "rwy18_weather_state": conditions["18"]["weather_state"],
                "runway_wind": conditions, "reason_codes": reasons,
                "p_od07": None, "p_od25": None, "p_rwy18_weather_usable": None,
                "probability_status": "not_available_for_deterministic_baseline"}


def prediction_features(weather, initial_direction, lead_hours):
    speed = number(weather.get("wind_speed_kt"))
    direction = number(weather.get("wind_from_deg_true"))
    gust = number(weather.get("wind_gust_kt"))
    if speed is None or speed < 0 or (speed > 0 and (direction is None or not 0 <= direction <= 360)):
        return None
    theta = math.radians(direction or 0)
    return [-speed * math.sin(theta), -speed * math.cos(theta),
            gust if gust is not None else speed, float(gust is None),
            float(initial_direction == "07"), float(initial_direction == "25"), float(lead_hours)]


FEATURE_NAMES = ["wind_u_kt", "wind_v_kt", "gust_or_mean_kt", "gust_missing",
                 "initial_od07", "initial_od25", "lead_time_hours"]
