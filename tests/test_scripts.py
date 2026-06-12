from unittest.mock import patch

from notification_rake import main, run_script, script_names
from notification_rake.models import VehicleListing


def test_script_names():
    names = script_names()
    assert "health" in names
    assert "pipeline" in names
    assert "ingest" in names
    assert "hasura_track" in names


def test_main_help():
    assert main(["help"]) == 0


def test_main_unknown():
    assert main(["not-a-command"]) == 2


def test_run_ingest():
    sample = [VehicleListing(source="c", source_listing_id="1", title="test")]
    with patch("notification_rake.workflow.ingest", return_value=sample):
        assert run_script("ingest") == 0
