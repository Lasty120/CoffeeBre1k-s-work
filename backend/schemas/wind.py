"""Wind condition parameters schema."""

from pydantic import BaseModel, Field, field_validator


class WindParams(BaseModel):
    """Ambient wind conditions at the time of mission execution.

    Args:
        speed_mps (float): Wind speed in metres per second.  Must be >= 0.
        direction_deg (float): Meteorological wind direction in degrees [0, 360).
            Represents the compass bearing *from which* the wind is blowing,
            following the standard met convention (0° = wind from North,
            90° = wind from East, etc.).

    Returns:
        WindParams: Validated wind parameters instance.

    Raises:
        ValueError: If direction_deg is not in the half-open interval [0, 360).
    """

    speed_mps: float = Field(ge=0, description="Wind speed in m/s (>= 0).")
    direction_deg: float = Field(
        description="Meteorological wind-from direction in degrees, [0, 360)."
    )

    @field_validator("direction_deg")
    @classmethod
    def validate_direction(cls, v: float) -> float:
        """Validates that wind direction lies within the half-open interval [0, 360).

        Args:
            v (float): Raw direction value in degrees.

        Returns:
            float: The validated direction value, unchanged.

        Raises:
            ValueError: If v < 0 or v >= 360.
        """
        if not (0.0 <= v < 360.0):
            raise ValueError(
                f"direction_deg must be in [0, 360), got {v}. "
                "Use 0 for North, 90 for East, 180 for South, 270 for West."
            )
        return v
