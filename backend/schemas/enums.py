"""Enumeration types shared across request and response schemas."""

from enum import Enum


class SurveyType(str, Enum):
    """Sensor/payload type used during the mission.

    Inherits from str so FastAPI serialises values as plain JSON strings
    and Swagger renders a dropdown with exact string literals.
    """

    RGB = "RGB"
    MULTISPECTRAL = "multispectral"
    IR = "IR"
    LIDAR = "LiDAR"
    GEOPHYSICAL = "geophysical"


class OptimizationCriterion(str, Enum):
    """Objective function the planner should optimise.

    Attributes:
        MIN_TIME: Minimise total wall-clock time until all drones land.
        MIN_TOTAL_FLIGHT: Minimise the sum of all individual flight durations.
    """

    MIN_TIME = "min_time"
    MIN_TOTAL_FLIGHT = "min_total_flight"
