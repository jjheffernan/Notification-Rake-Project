from contextlib import ExitStack
from unittest.mock import patch

from notification_rake.models import VehicleListing
from notification_rake.storage import UpsertResult
from notification_rake.transform import FALLBACK_CATALOG
from notification_rake.workflow import PipelineResult, run_pipeline


def test_run_pipeline():
    sample = [
        VehicleListing(
            source="craigslist",
            source_listing_id="1",
            title="2019 Toyota Camry",
            year=2019,
            price=12500.0,
            make="Toyota",
            model="Camry",
            longitude=-122.4,
            latitude=37.7,
        )
    ]
    upserted = [UpsertResult("uuid-1", sample[0], True)]
    catalog = list(FALLBACK_CATALOG)

    with ExitStack() as stack:
        stack.enter_context(
            patch("notification_rake.workflow.pipeline.ingest", return_value=sample)
        )
        stack.enter_context(
            patch("notification_rake.workflow.pipeline.seed_catalog", return_value=8)
        )
        stack.enter_context(
            patch("notification_rake.workflow.pipeline.store_raw_listings", return_value=(1, 1))
        )
        stack.enter_context(
            patch("notification_rake.workflow.pipeline.start_job", return_value="job-1")
        )
        stack.enter_context(patch("notification_rake.workflow.pipeline.finish_job"))
        stack.enter_context(
            patch("notification_rake.workflow.pipeline.load_catalog", return_value=catalog)
        )
        stack.enter_context(
            patch("notification_rake.workflow.pipeline.geocode_listings", return_value=sample)
        )
        stack.enter_context(
            patch("notification_rake.workflow.pipeline.upsert_listings", return_value=upserted)
        )
        stack.enter_context(
            patch("notification_rake.workflow.pipeline.notify_new_listings", return_value=1)
        )
        stack.enter_context(
            patch(
                "notification_rake.workflow.pipeline.search_within_radius",
                return_value=[{"id": "uuid-1"}],
            )
        )
        result = run_pipeline(dsn="postgresql://test/test")

    assert isinstance(result, PipelineResult)
    assert result.fetched == 1
    assert result.raw_stored == 1
    assert result.matched == 1
    assert result.upserted == 1
    assert result.new == 1
    assert result.alerted == 1
    assert result.in_radius == 1
