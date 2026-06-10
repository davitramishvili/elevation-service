"""API response models."""

from pydantic import BaseModel, Field


class ElevationResponse(BaseModel):
    latitude: float = Field(..., json_schema_extra={"example": 52.5163})
    longitude: float = Field(..., json_schema_extra={"example": 13.3777})
    elevation_m: float = Field(..., json_schema_extra={"example": 35.2})
    resolved_address: str | None = Field(
        None, description="The full address the input was resolved to"
    )
    data_origin: str | None = Field(
        None, description="Federal-state dataset the elevation came from, e.g. DE-BB"
    )
    attribution: str | None = Field(
        None, description="Data licences for the geocoding and elevation sources"
    )


class ErrorDetail(BaseModel):
    code: str = Field(..., json_schema_extra={"example": "ADDRESS_NOT_FOUND"})
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail
