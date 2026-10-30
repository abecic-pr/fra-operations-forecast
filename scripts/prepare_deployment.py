"""Copy only the public snapshots and wind artifacts needed by the hosted demo."""
import argparse
import json
from pathlib import Path
import shutil

FILES = (
    "forecast.json", "runway18-departures.json", "sources.json",
    "comparison/evaluation.json", "comparison/forecast.json", "comparison/discovery.json",
    "comparison/agent.json",
    "models/icon-eu-wind-v1/manifest.json", "models/icon-eu-wind-v1/model.joblib",
    "models/icon-eu-wind-v1/metrics.json", "models/wind-comparison-v1/manifest.json",
    "models/wind-comparison-v1/model.joblib", "models/wind-comparison-v1/metrics.json",
    "models/wind-comparison-v1/policy.json",
)


def prepare(source, destination):
    source, destination = Path(source), Path(destination)
    snapshot = json.loads((source / "forecast.json").read_text())
    if snapshot.get("schema_version") not in ("1.0", "1.1") or len(snapshot.get("forecast", [])) != 48:
        raise ValueError("Deployment needs a valid 48-hour forecast snapshot")
    destination.mkdir(parents=True, exist_ok=False)
    for name in FILES:
        if (source / name).is_file():
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source / name, target)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--output", type=Path, default=Path("deployment-data"))
    args = parser.parse_args()
    prepare(args.data_dir, args.output)
