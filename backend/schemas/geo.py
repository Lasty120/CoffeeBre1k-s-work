"""GeoJSON geometry and feature models compliant with RFC 7946.

Design notes
------------
frozen=True (ConfigDict)
    Makes every geometry instance *immutable* after construction — the same
    effect as a frozen dataclass.  This means:
      - Geometry objects can be used as dict keys or placed in sets.
      - Accidental mutation inside service/algorithm code raises a TypeError
        immediately instead of silently corrupting shared state.
      - Pydantic can cache the model's __hash__, giving a small speed benefit
        when the same geometry is validated multiple times.
    Trade-off: you cannot do  point.coordinates = (...)  after creation.
    To "modify" a geometry, create a new instance.

Coordinate conventions (RFC 7946 §3.1.1)
    Point / Polygon / MultiPolygon  →  (longitude, latitude)   — 2-tuple
    LineString (flight route)       →  (longitude, latitude, altitude_m) — 3-tuple
    Altitude is in **metres above WGS-84 ellipsoid** (not AGL).

Discriminated unions
    SurveyAreaGeometry and NfzGeometry use Pydantic's discriminated-union
    mechanism on the 'type' field, so Pydantic picks the correct model at
    parse time without trying both.  The discriminator is included in the
    OpenAPI schema, which makes Swagger UI show the two sub-schemas clearly.
"""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# Primitive geometry models
# ---------------------------------------------------------------------------


class PointGeometry(BaseModel):
    """GeoJSON Point geometry representing a single geographic location.

    Args:
        type (Literal['Point']): Fixed type discriminator, always 'Point'.
        coordinates (tuple[float, float]): [longitude, latitude] in WGS-84 degrees.
            Longitude must be in [-180, 180]; latitude in [-90, 90].

    Returns:
        PointGeometry: Immutable, validated point instance.

    Raises:
        ValueError: If longitude or latitude are outside their valid ranges.
    """

    model_config = ConfigDict(frozen=True)

    type: Literal["Point"] = "Point"
    coordinates: tuple[float, float]

    @field_validator("coordinates")
    @classmethod
    def validate_lon_lat(cls, v: tuple[float, float]) -> tuple[float, float]:
        """Validates that longitude and latitude are within WGS-84 bounds.

        Args:
            v (tuple[float, float]): Raw [longitude, latitude] pair.

        Returns:
            tuple[float, float]: The validated coordinate pair, unchanged.

        Raises:
            ValueError: If either value is outside the allowed range.
        """
        lon, lat = v
        if not (-180.0 <= lon <= 180.0):
            raise ValueError(f"Longitude must be in [-180, 180], got {lon}.")
        if not (-90.0 <= lat <= 90.0):
            raise ValueError(f"Latitude must be in [-90, 90], got {lat}.")
        return v


class PolygonGeometry(BaseModel):
    """GeoJSON Polygon geometry (outer ring + optional holes).

    Args:
        type (Literal['Polygon']): Fixed type discriminator.
        coordinates (list[list[tuple[float, float]]]): List of linear rings.
            The first ring is the exterior boundary; subsequent rings are holes.
            Each ring must have at least 4 positions and be closed
            (first position == last position).

    Returns:
        PolygonGeometry: Immutable, validated polygon instance.

    Raises:
        ValueError: If any ring has fewer than 4 points or is not closed.
    """

    model_config = ConfigDict(frozen=True)

    type: Literal["Polygon"] = "Polygon"
    coordinates: list[list[tuple[float, float]]]

    @field_validator("coordinates")
    @classmethod
    def validate_rings(
        cls, v: list[list[tuple[float, float]]]
    ) -> list[list[tuple[float, float]]]:
        """Validates that every linear ring is closed and has enough points.

        Args:
            v (list[list[tuple[float, float]]]): List of rings to validate.

        Returns:
            list[list[tuple[float, float]]]: The validated ring list, unchanged.

        Raises:
            ValueError: If a ring has fewer than 4 points or is not closed.
        """
        for i, ring in enumerate(v):
            if len(ring) < 4:
                raise ValueError(
                    f"Ring {i} must have at least 4 positions (got {len(ring)}). "
                    "A valid closed ring repeats the first point as the last."
                )
            if ring[0] != ring[-1]:
                raise ValueError(
                    f"Ring {i} is not closed: first point {ring[0]} "
                    f"!= last point {ring[-1]}."
                )
        return v


class MultiPolygonGeometry(BaseModel):
    """GeoJSON MultiPolygon geometry: a collection of polygons.

    Args:
        type (Literal['MultiPolygon']): Fixed type discriminator.
        coordinates (list[list[list[tuple[float, float]]]]): List of polygon
            coordinate arrays, each following the same ring rules as
            PolygonGeometry.

    Returns:
        MultiPolygonGeometry: Immutable, validated multi-polygon instance.
    """

    model_config = ConfigDict(frozen=True)

    type: Literal["MultiPolygon"] = "MultiPolygon"
    coordinates: list[list[list[tuple[float, float]]]]


class LineStringGeometry(BaseModel):
    """GeoJSON LineString geometry used to represent a UAV flight route.

    Each coordinate is a 3-tuple: [longitude, latitude, altitude_m].
    The third value (altitude) follows RFC 7946 §3.1.1 — it is the height
    above the WGS-84 ellipsoid in **metres**.  In practice, for mission
    planning purposes this is treated as approximate AMSL altitude.

    Args:
        type (Literal['LineString']): Fixed type discriminator.
        coordinates (list[tuple[float, float, float]]): Ordered list of
            [longitude, latitude, altitude_m] waypoints forming the route.
            Requires at least 2 points to form a valid line.

    Returns:
        LineStringGeometry: Immutable, validated route geometry instance.

    Raises:
        ValueError: If fewer than 2 waypoints are provided.
    """

    model_config = ConfigDict(frozen=True)

    type: Literal["LineString"] = "LineString"
    coordinates: list[tuple[float, float, float]]

    @field_validator("coordinates")
    @classmethod
    def validate_min_points(
        cls, v: list[tuple[float, float, float]]
    ) -> list[tuple[float, float, float]]:
        """Validates that the LineString contains at least 2 waypoints.

        Args:
            v (list[tuple[float, float, float]]): Raw waypoint list.

        Returns:
            list[tuple[float, float, float]]: The validated waypoint list.

        Raises:
            ValueError: If the list contains fewer than 2 points.
        """
        if len(v) < 2:
            raise ValueError(
                f"LineString must have at least 2 waypoints, got {len(v)}."
            )
        return v


# ---------------------------------------------------------------------------
# Discriminated union aliases
# ---------------------------------------------------------------------------

SurveyAreaGeometry = Annotated[
    PolygonGeometry | MultiPolygonGeometry,
    Field(discriminator="type"),
]
"""Union type for survey area input: accepts Polygon or MultiPolygon only."""

NfzGeometry = Annotated[
    PolygonGeometry | MultiPolygonGeometry,
    Field(discriminator="type"),
]
"""Union type for no-fly zone input: accepts Polygon or MultiPolygon only."""

AnyGeometry = Annotated[
    PointGeometry | PolygonGeometry | MultiPolygonGeometry | LineStringGeometry,
    Field(discriminator="type"),
]
"""Union of all supported geometry types, used inside GeoJSON Feature."""


# ---------------------------------------------------------------------------
# GeoJSON Feature and FeatureCollection
# ---------------------------------------------------------------------------


class GeoJSONFeature(BaseModel):
    """GeoJSON Feature object wrapping a geometry with optional metadata.

    Args:
        type (Literal['Feature']): Fixed type discriminator.
        geometry (AnyGeometry): One of Point, Polygon, MultiPolygon, LineString.
        properties (dict[str, Any] | None): Arbitrary key/value metadata,
            e.g. drone_id, estimated_duration_min.  May be null per RFC 7946.

    Returns:
        GeoJSONFeature: Validated feature instance.
    """

    type: Literal["Feature"] = "Feature"
    geometry: AnyGeometry
    properties: dict[str, Any] | None = None


class GeoJSONFeatureCollection(BaseModel):
    """GeoJSON FeatureCollection — the top-level object returned by the API.

    Can be passed directly to Leaflet's L.geoJSON() or OpenLayers'
    ol.format.GeoJSON without any transformation on the frontend side.

    Args:
        type (Literal['FeatureCollection']): Fixed type discriminator.
        features (list[GeoJSONFeature]): Zero or more Feature objects.

    Returns:
        GeoJSONFeatureCollection: Validated collection instance.
    """

    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[GeoJSONFeature]
