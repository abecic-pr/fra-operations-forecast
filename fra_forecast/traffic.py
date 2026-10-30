"""Published FRA movements, without inferred runway assignments or aircraft positions."""
from datetime import datetime, timedelta
from pathlib import Path
from .departures import fetch_departures
from .domain import UTC, iso
from .sources import SourceClient, write_json


def refresh_traffic(root, now=None, client=None, hours=48):
    root = Path(root)
    now = now or datetime.now(UTC)
    client = client or SourceClient(root)
    flights, sources = [], {}
    for kind, operation in (("arrivals", "landing"), ("departures", "departure")):
        records, source = fetch_departures(client, now, now + timedelta(hours=hours), flighttype=kind)
        sources[kind] = source
        for record in records:
            flights.append({"id": kind + ":" + str(record["flight_id"]),
                            "number": record["flight_number"], "operation": operation,
                            "airport": record["destination"], "aircraft_type": record["aircraft_type"],
                            "scheduled_at": record["scheduled_departure_at"],
                            "estimated_at": record["estimated_departure_at"],
                            "time_basis": "published_board_time_not_runway_movement",
                            "assigned_runway": None, "assignment_status": "unavailable",
                            "position": None, "status": record["status"],
                            "source_url": source["url"], "fetched_at": record["fetched_at"]})
    result = {"schema_version": "1.0", "generated_at": iso(now), "sources": sources,
              "flights": sorted(flights, key=lambda f: (f["estimated_at"] or f["scheduled_at"], f["id"])),
              "limitations": ["Public passenger board may omit cargo and private services.",
                              "No confirmed runway assignments, aircraft positions or wheels-off/touchdown times.",
                              "Coverage is best-effort; inspect each source's completeness and errors."]}
    write_json(root / "traffic.json", result)
    return result


if __name__ == "__main__":
    result = refresh_traffic(Path("data"))
    print(f"Saved {len(result['flights'])} published airport movements; assignments and positions unavailable.")
