"""Asset requests and representations."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, JsonValue

from a13n_service.resources.uploads.schemas import FileName, UploadId


class AssetCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    upload_id: UploadId
    name: FileName


class Asset(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    workspace_id: str
    name: str
    content_type: str
    size: int
    digest: str
    source: dict[str, JsonValue] | None
    retired_at: datetime | None
    version: int
    created_by_id: str
    created_at: datetime
    updated_at: datetime


class AssetPage(BaseModel):
    items: list[Asset]
    next_cursor: str | None
