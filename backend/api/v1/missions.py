"""Mission planning router — v1.

Currently contains one stub endpoint:
    POST /missions/plan

The stub validates the full incoming payload, generates a bounding-box
perimeter route for each drone (useful for frontend integration testing),
and returns a valid MissionPlanningResponse.  The real optimisation algorithm
(OR-Tools / custom solver) will replace _build_stub_plan() in Phase 2.
"""

import logging
import math

from fastapi import APIRouter, HTTPException, status

from schemas.geo import (
    GeoJSONFeature,
    GeoJSONFeatureCollection,
    LineStringGeometry,
    PointGeometry,
)
from schemas.mission_request import MissionPlanningRequest
from schemas.mission_response import DroneFlightPlan, MissionPlanningResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/missions", tags=["missions"])


# ---------------------------------------------------------------------------
# Internal stub helpers
# ---------------------------------------------------------------------------


def _extract_bbox(request: MissionPlanningRequest) -> tuple[float, float, float, float]:
    """Extracts the axis-aligned bounding box of the survey area.

    Args:
        request (MissionPlanningRequest): Validated mission planning request.

    Returns:
        tuple[float, float, float, float]: (min_lon, min_lat, max_lon, max_lat).
    """
    area = request.survey_area

    if area.type == "Polygon":
        all_coords = [pt for ring in area.coordinates for pt in ring]
    else:
        all_coords = [
            pt
            for polygon in area.coordinates
            for ring in polygon
            for pt in ring
        ]

    lons = [c[0] for c in all_coords]
    lats = [c[1] for c in all_coords]
    return min(lons), min(lats), max(lons), max(lats)


def _bbox_perimeter_route(
    min_lon: float,
    min_lat: float,
    max_lon: float,
    max_lat: float,
    altitude_m: float,
) -> LineStringGeometry:
    """Builds a closed rectangular perimeter LineString over the bbox.

    The route visits all four corners and returns to the start, giving a
    visually meaningful stub track that the frontend can render immediately.

    Args:
        min_lon (float): Western longitude boundary.
        min_lat (float): Southern latitude boundary.
        max_lon (float): Eastern longitude boundary.
        max_lat (float): Northern latitude boundary.
        altitude_m (float): Flight altitude in metres (AMSL approx.).

    Returns:
        LineStringGeometry: Five-waypoint closed perimeter route.
    """
    return LineStringGeometry(
        coordinates=[
            (min_lon, min_lat, altitude_m),
            (max_lon, min_lat, altitude_m),
            (max_lon, max_lat, altitude_m),
            (min_lon, max_lat, altitude_m),
            (min_lon, min_lat, altitude_m),
        ]
    )


def _haversine_km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Calculates the great-circle distance between two WGS-84 points.

    Args:
        lon1 (float): Longitude of the first point in degrees.
        lat1 (float): Latitude of the first point in degrees.
        lon2 (float): Longitude of the second point in degrees.
        lat2 (float): Latitude of the second point in degrees.

    Returns:
        float: Distance in kilometres.
    """
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lam = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lam / 2) ** 2
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _estimate_duration_min(route: LineStringGeometry, speed_mps: float) -> float:
    """Estimates flight duration for a route at a given groundspeed.

    Args:
        route (LineStringGeometry): Waypoint sequence to travel along.
        speed_mps (float): Groundspeed in metres per second.

    Returns:
        float: Estimated duration in minutes, rounded to two decimal places.
    """
    total_km = sum(
        _haversine_km(
            route.coordinates[i][0], route.coordinates[i][1],
            route.coordinates[i + 1][0], route.coordinates[i + 1][1],
        )
        for i in range(len(route.coordinates) - 1)
    )
    distance_m = total_km * 1000.0
    return round(distance_m / speed_mps / 60.0, 2)


def _resolve_home_point(request: MissionPlanningRequest, home_point_id: str | None) -> PointGeometry:
    """Resolves a drone's home point geometry from the request's home_points list.

    Falls back to the first declared home point when home_point_id is None.

    Args:
        request (MissionPlanningRequest): The fully validated mission request.
        home_point_id (str | None): The drone's home_point_id field value.

    Returns:
        PointGeometry: The resolved ground point geometry.
    """
    if home_point_id is None:
        return request.home_points[0].geometry

    for hp in request.home_points:
        if hp.id == home_point_id:
            return hp.geometry

    return request.home_points[0].geometry


def _build_stub_plan(request: MissionPlanningRequest) -> MissionPlanningResponse:
    """Generates a stub mission plan with bounding-box perimeter routes.

    This function is a placeholder for the real optimisation solver (Phase 2).
    For each drone it:
      1. Resolves its home point.
      2. Builds a rectangular route around the survey area bbox.
      3. Estimates flight duration via Haversine distance + cruise speed.
      4. Wraps everything in the response schema.

    Args:
        request (MissionPlanningRequest): Validated mission planning request.

    Returns:
        MissionPlanningResponse: A valid, schema-compliant stub response.
    """
    min_lon, min_lat, max_lon, max_lat = _extract_bbox(request)

    drone_plans: list[DroneFlightPlan] = []
    features: list[GeoJSONFeature] = []

    for drone in request.drones:
        altitude_m = min(drone.max_altitude_agl_m, 100.0)
        route = _bbox_perimeter_route(min_lon, min_lat, max_lon, max_lat, altitude_m)
        home_point = _resolve_home_point(request, drone.home_point_id)
        duration_min = _estimate_duration_min(route, drone.cruise_speed_mps)

        plan = DroneFlightPlan(
            drone_id=drone.id,
            route=route,
            altitude_m=altitude_m,
            speed_mps=drone.cruise_speed_mps,
            takeoff_point=home_point,
            landing_point=home_point,
            estimated_duration_min=duration_min,
            waypoints_count=len(route.coordinates),
        )
        drone_plans.append(plan)

        features.append(
            GeoJSONFeature(
                geometry=route,
                properties={
                    "drone_id": drone.id,
                    "drone_model": drone.model,
                    "feature_type": "route",
                    "altitude_m": altitude_m,
                    "estimated_duration_min": duration_min,
                },
            )
        )
        features.append(
            GeoJSONFeature(
                geometry=home_point,
                properties={
                    "drone_id": drone.id,
                    "feature_type": "home_point",
                },
            )
        )

    total_time = max((p.estimated_duration_min for p in drone_plans), default=0.0)

    return MissionPlanningResponse(
        optimization_criterion=request.optimization_criterion,
        survey_type=request.survey_type,
        total_estimated_time_min=total_time,
        drone_plans=drone_plans,
        geojson=GeoJSONFeatureCollection(features=features),
    )


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post(
    "/plan",
    response_model=MissionPlanningResponse,
    status_code=status.HTTP_200_OK,
    summary="Plan a multi-UAV mission",
    description=(
        "Accepts a fully described mission scenario and returns individual "
        "flight plans for each UAV in the fleet, along with a combined "
        "GeoJSON FeatureCollection suitable for direct map rendering. "
        "**Phase 1 stub**: routes are bounding-box perimeters. "
        "Real optimisation replaces this in Phase 2."
    ),
)
async def plan_mission(request: MissionPlanningRequest) -> MissionPlanningResponse:
    """Computes and returns flight plans for all UAVs in the fleet.

    Args:
        request (MissionPlanningRequest): Validated mission planning payload.

    Returns:
        MissionPlanningResponse: Individual drone plans + combined GeoJSON.

    Raises:
        HTTPException 422: Automatically by FastAPI when Pydantic validation fails.
        HTTPException 500: If an unexpected error occurs in the stub planner.
    """
    logger.info(
        "Mission plan requested | drones=%d | survey_type=%s | criterion=%s",
        len(request.drones),
        request.survey_type.value,
        request.optimization_criterion.value,
    )

    try:
        response = _build_stub_plan(request)
    except Exception as exc:
        logger.exception("Unexpected error in stub planner: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal planner error. See server logs for details.",
        ) from exc

    logger.info(
        "Mission plan generated | drones=%d | total_time_min=%.2f",
        len(response.drone_plans),
        response.total_estimated_time_min,
    )
    return response
