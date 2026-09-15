"""UAV (drone) specification schema."""

from enum import Enum

from pydantic import BaseModel, Field

from schemas.enums import SurveyType


class DroneKind(str, Enum):
    """Airframe type, determines takeoff/landing model and flight physics."""

    MULTIROTOR = "multirotor"
    FIXED_WING = "fixed_wing"


class DroneSpec(BaseModel):
    """Represents technical characteristics of a single UAV available for mission planning.

    Args:
        id (str): Unique identifier of this drone instance within the fleet.
        model (str): Human-readable model name, e.g. "Geoscan 201".
        kind (DroneKind): Airframe type - affects takeoff/landing constraints.
        max_flight_time_min (float): Maximum flight time on a single battery, in minutes.
        cruise_speed_mps (float): Cruise (nominal) airspeed in meters per second.
        max_wind_speed_mps (float): Maximum wind speed the drone can safely operate in.
        max_altitude_agl_m (float): Maximum permitted altitude above ground level, in meters.
        max_payload_kg (float | None): Maximum payload weight in kilograms, if constrained.
        supported_survey_types (list[SurveyType]): Survey types this drone's payload supports.
        max_range_km (float | None): Maximum communication/link range in kilometers.
        home_point_id (str | None): Identifier of the assigned takeoff/landing point, if fixed.

    Returns:
        DroneSpec: Validated drone specification instance.
    """

    id: str
    model: str
    kind: DroneKind
    max_flight_time_min: float = Field(gt=0)
    cruise_speed_mps: float = Field(gt=0)
    max_wind_speed_mps: float = Field(ge=0)
    max_altitude_agl_m: float = Field(gt=0)
    max_payload_kg: float | None = Field(default=None, gt=0)
    supported_survey_types: list[SurveyType] = Field(min_length=1)
    max_range_km: float | None = Field(default=None, gt=0)
    home_point_id: str | None = None
