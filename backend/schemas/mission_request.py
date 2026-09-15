"""Incoming request contract for the mission planning endpoint."""

from pydantic import BaseModel, Field, model_validator

from schemas.drone import DroneSpec
from schemas.enums import OptimizationCriterion, SurveyType
from schemas.geo import NfzGeometry, PointGeometry, SurveyAreaGeometry
from schemas.wind import WindParams


class HomePoint(BaseModel):
    """A named takeoff/landing location referenced by drones via home_point_id.

    Args:
        id (str): Unique identifier for this ground point within the request.
            Must match the home_point_id values used in DroneSpec entries.
        geometry (PointGeometry): WGS-84 longitude/latitude of the ground point.

    Returns:
        HomePoint: Validated home point instance.
    """

    id: str
    geometry: PointGeometry


class MissionPlanningRequest(BaseModel):
    """Full input payload for a UAV mission planning calculation.

    Args:
        survey_area (SurveyAreaGeometry): GeoJSON Polygon or MultiPolygon
            defining the area to be surveyed.
        no_fly_zones (list[NfzGeometry]): Zero or more GeoJSON Polygon /
            MultiPolygon geometries that UAVs must not enter.  Send an empty
            list if there are no restrictions.
        home_points (list[HomePoint]): Named ground control points used as
            takeoff and/or landing locations.  At least one point is required.
        drones (list[DroneSpec]): Fleet of UAVs available for this mission.
            At least one drone is required.
        wind (WindParams): Current ambient wind conditions at mission time.
        survey_type (SurveyType): Sensor payload type for the mission.
        optimization_criterion (OptimizationCriterion): Objective the planner
            should optimise — either minimise total wall-clock time or minimise
            the sum of all individual flight durations.

    Returns:
        MissionPlanningRequest: Validated, self-consistent mission request.

    Raises:
        ValueError: If a drone does not support the requested survey_type, or
            if a drone references an unknown home_point_id.
    """

    survey_area: SurveyAreaGeometry
    no_fly_zones: list[NfzGeometry] = Field(default_factory=list)
    home_points: list[HomePoint] = Field(min_length=1)
    drones: list[DroneSpec] = Field(min_length=1)
    wind: WindParams
    survey_type: SurveyType
    optimization_criterion: OptimizationCriterion

    @model_validator(mode="after")
    def validate_fleet_consistency(self) -> "MissionPlanningRequest":
        """Validates cross-field business rules after all fields are parsed.

        Checks performed:
          1. Every drone in the fleet supports the requested survey_type.
          2. Every non-null home_point_id references an existing HomePoint.

        Args:
            self: The fully-parsed MissionPlanningRequest instance.

        Returns:
            MissionPlanningRequest: The instance, unchanged if valid.

        Raises:
            ValueError: On the first drone that violates either check.
        """
        known_point_ids: set[str] = {hp.id for hp in self.home_points}

        for drone in self.drones:
            if self.survey_type not in drone.supported_survey_types:
                supported = [t.value for t in drone.supported_survey_types]
                raise ValueError(
                    f"Drone '{drone.id}' (model: {drone.model}) does not support "
                    f"survey type '{self.survey_type.value}'. "
                    f"Its payload supports: {supported}."
                )

            if drone.home_point_id is not None and drone.home_point_id not in known_point_ids:
                raise ValueError(
                    f"Drone '{drone.id}' references unknown home_point_id "
                    f"'{drone.home_point_id}'. "
                    f"Declared home_point ids: {sorted(known_point_ids)}."
                )

        return self
