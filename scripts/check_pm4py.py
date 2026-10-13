"""Exercise the optional native OCEL 2 JSON import boundary with synthetic data."""

import json
import tempfile
from importlib.metadata import version
from pathlib import Path

import pm4py


def main() -> None:
    """Verify optional availability and exact OCEL event/object/relation preservation."""
    fixture = {
        "objectTypes": [{"name": "request", "attributes": []}],
        "eventTypes": [{"name": "received", "attributes": []}],
        "objects": [{"id": "request-1", "type": "request", "attributes": [], "relationships": []}],
        "events": [
            {
                "id": "event-1",
                "type": "received",
                "time": "2026-01-01T00:00:00Z",
                "attributes": [],
                "relationships": [{"objectId": "request-1", "qualifier": "case"}],
            }
        ],
    }
    with tempfile.TemporaryDirectory(prefix="careops-pm4py-") as directory:
        path = Path(directory) / "synthetic.jsonocel"
        path.write_text(json.dumps(fixture), encoding="utf-8")
        log = pm4py.read_ocel2_json(str(path))
        if (
            list(log.events["ocel:eid"]) != ["event-1"]
            or list(log.events["ocel:activity"]) != ["received"]
            or list(log.objects["ocel:oid"]) != ["request-1"]
            or list(log.relations["ocel:oid"]) != ["request-1"]
            or list(log.relations["ocel:qualifier"]) != ["case"]
        ):
            message = "PM4Py did not preserve the synthetic OCEL import boundary"
            raise RuntimeError(message)
    print(f"PM4Py {version('pm4py')}: synthetic OCEL 2 JSON import passed")  # noqa: T201


if __name__ == "__main__":
    main()
