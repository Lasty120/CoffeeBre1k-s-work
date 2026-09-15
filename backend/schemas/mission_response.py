"""Outgoing response contract for the mission planning endpoint."""

from pydantic import BaseModel

from schemas.enums import OptimizationCriterion, SurveyType
from schemas.geo import GeoJSONFeatureCollection, LineStringGeometry, PointGeometry


class DroneFlightPlan(BaseModel):
    """Individual flight assignment computed for a single UAV.

    Args:
        drone_id (str): Matches the DroneSpec.id from the request.
        route (LineStringGeometry): Ordered waypoints as [lon, lat, alt_m].
            Suitable for direct rendering on a Leaflet/OpenLayers map.
        altitude_m (float): Nominal operating altitude in metres (AMSL approx.).
        speed_mps (float): Planned groundspeed in metres per second.
        takeoff_point (PointGeometry): Departure location [lon, lat].
        landing_point (PointGeometry): Arrival location [lon, lat].
        estimated_duration_min (float): Estimated flight time in minutes.
        waypoints_count (int): Total number of waypoints in the route
            (convenience field, equals len(route.coordinates)).

    Returns:
        DroneFlightPlan: Validated flight plan for one UAV.
    """

    drone_id: str
    route: LineStringGeometry
    altitude_m: float
    speed_mps: float
    takeoff_point: PointGeometry
    landing_point: PointGeometry
    estimated_duration_min: float
    waypoints_count: int


class MissionPlanningResponse(BaseModel):
    """Complete mission planning result returned by POST /api/v1/missions/plan.

    Contains two representations of the same data to serve different frontend
    consumers simultaneously:
      - ``geojson``      → pass directly to L.geoJSON() / ol.format.GeoJSON()
      - ``drone_plans``  → structured data for the UI sidebar / data table

    Args:
        optimization_criterion (OptimizationCriterion): The objective that was
            optimised, echoed back from the request for UI labelling.
        survey_type (SurveyType): The sensor type used, echoed from request.
        total_estimated_time_min (float): Wall-clock time from first takeoff to
            last landing across the entire fleet, in minutes.
        drone_plans (list[DroneFlightPlan]): One plan per UAV in the fleet.
        geojson (GeoJSONFeatureCollection): All routes (and optionally home
            points, NFZ outlines) combined into a single FeatureCollection.
            Each Feature carries a ``properties`` dict with at minimum
            ``drone_id`` and ``feature_type`` keys.

    Returns:
        MissionPlanningResponse: Validated response ready for JSON serialisation.
    """

    optimization_criterion: OptimizationCriterion
    survey_type: SurveyType
    total_estimated_time_min: float
    drone_plans: list[DroneFlightPlan]
    geojson: GeoJSONFeatureCollection
