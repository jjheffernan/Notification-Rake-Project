from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class VehicleListing(BaseModel):
    """Normalized listing — see docs/functions.md and specs.md."""

    source: str
    source_listing_id: str
    title: str | None = None
    description: str | None = None
    make: str | None = None
    model: str | None = None
    year: int | None = None
    mileage: int | None = None
    price: float | None = None
    vin: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    seller_name: str | None = None
    seller_type: str | None = None
    country: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    image_urls: list[str] = Field(default_factory=list)
    scraped_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
