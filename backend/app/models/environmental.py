"""Pydantic models representing environmental variables and scientific assessments.

All measurement fields are optional to allow the conversational agent to detect
missing environmental information and formulate targeted clarification questions.
"""

import re
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, ConfigDict, field_validator


class SoilData(BaseModel):
    """Soil health indicators."""
    model_config = ConfigDict(extra="ignore")

    soil_ph: Optional[Union[float, str]] = Field(
        default=None,
        description="Soil pH on standard 0-14 logarithmic scale or category",
    )
    soil_organic_carbon: Optional[Union[float, str]] = Field(
        default=None,
        description="Soil Organic Carbon (SOC) percentage or g/kg",
    )
    soil_moisture: Optional[Union[float, str]] = Field(
        default=None,
        description="Volumetric soil water content or moisture percentage (0-100)",
    )

    @field_validator("soil_ph", "soil_organic_carbon", "soil_moisture", mode="before")
    @classmethod
    def clean_soil_metrics(cls, v: Any) -> Any:
        if isinstance(v, str):
            cleaned = v.replace("%", "").strip()
            try:
                return float(cleaned)
            except ValueError:
                return v.strip()
        return v

    @field_validator("soil_ph")
    @classmethod
    def validate_ph(cls, v: Any) -> Any:
        if isinstance(v, (int, float)):
            if v < 0.0 or v > 14.0:
                raise ValueError(f"Soil pH must be between 0.0 and 14.0, got {v}")
        return v

    @field_validator("soil_moisture")
    @classmethod
    def validate_moisture(cls, v: Any) -> Any:
        if isinstance(v, (int, float)):
            if v < 0.0 or v > 100.0:
                raise ValueError(f"Soil moisture must be between 0.0 and 100.0%, got {v}")
        return v

    @field_validator("soil_organic_carbon")
    @classmethod
    def validate_soc(cls, v: Any) -> Any:
        if isinstance(v, (int, float)):
            if v < 0.0:
                raise ValueError(f"Soil organic carbon cannot be negative, got {v}")
        return v


class ClimateData(BaseModel):
    """Atmospheric and meteorological metrics."""
    model_config = ConfigDict(extra="ignore")

    temperature: Optional[Union[float, str]] = Field(
        default=None,
        description="Mean ambient temperature in degrees Celsius or descriptor",
    )
    rainfall: Optional[Union[float, str]] = Field(
        default=None,
        description="Mean precipitation in millimeters (annual or seasonal) or regime (e.g. low, semi-arid)",
    )

    @field_validator("temperature", "rainfall", mode="before")
    @classmethod
    def clean_climate_metrics(cls, v: Any) -> Any:
        if isinstance(v, str):
            stripped = v.strip()
            num_match = re.match(r"^([0-9]+(?:\.[0-9]+)?)\s*(?:mm|°?c|celsius)?$", stripped, re.IGNORECASE)
            if num_match:
                try:
                    return float(num_match.group(1))
                except ValueError:
                    pass
            return stripped
        return v

    @field_validator("rainfall")
    @classmethod
    def validate_rainfall(cls, v: Any) -> Any:
        if isinstance(v, (int, float)):
            if v < 0.0:
                raise ValueError(f"Rainfall cannot be negative, got {v}")
        return v

    @field_validator("temperature")
    @classmethod
    def validate_temp(cls, v: Any) -> Any:
        if isinstance(v, (int, float)):
            if v < -60.0 or v > 70.0:
                raise ValueError(f"Temperature must be between -60.0 and 70.0 C, got {v}")
        return v


class LandData(BaseModel):
    """Land classification and terrain properties."""
    model_config = ConfigDict(extra="ignore")

    land_use: Optional[str] = Field(
        default=None,
        description="Land utilization type (e.g., agriculture, agroforestry, pasture, conservation)",
    )
    land_cover: Optional[str] = Field(
        default=None,
        description="Physical surface land cover (e.g., dense canopy, grassland, shrubland, bare soil)",
    )


class BiodiversityData(BaseModel):
    """Ecosystem biodiversity and species metrics."""
    model_config = ConfigDict(extra="ignore")

    species_richness: Optional[int] = Field(
        default=None,
        ge=0,
        description="Count of distinct indigenous or observed species",
    )
    habitat_diversity: Optional[Union[float, str]] = Field(
        default=None,
        description="Habitat diversity measure (Shannon/Simpson index or categorical level)",
    )


class HumanImpactData(BaseModel):
    """Anthropogenic stressors and ecological disturbances."""
    model_config = ConfigDict(extra="ignore")

    pollution: Optional[str] = Field(
        default=None,
        description="Pollution severity or contaminant type (e.g., low, moderate, heavy metals, agricultural runoff)",
    )
    deforestation: Optional[str] = Field(
        default=None,
        description="Deforestation pressure or historical degradation status (e.g., none, fragmented, clear-cut)",
    )


class LocationData(BaseModel):
    """Spatial coordinates and ecoregion context."""
    model_config = ConfigDict(extra="ignore")

    region: Optional[str] = Field(
        default=None,
        description="Geographic area, biome, or ecoregion name",
    )
    latitude: Optional[float] = Field(
        default=None,
        ge=-90.0,
        le=90.0,
        description="Latitude in decimal degrees (-90 to +90)",
    )
    longitude: Optional[float] = Field(
        default=None,
        ge=-180.0,
        le=180.0,
        description="Longitude in decimal degrees (-180 to +180)",
    )


class EnvironmentalData(BaseModel):
    """Unified composite environmental profile combining all sub-domains."""
    model_config = ConfigDict(extra="ignore")

    soil: SoilData = Field(default_factory=SoilData)
    climate: ClimateData = Field(default_factory=ClimateData)
    land: LandData = Field(default_factory=LandData)
    biodiversity: BiodiversityData = Field(default_factory=BiodiversityData)
    human_impact: HumanImpactData = Field(default_factory=HumanImpactData)
    location: LocationData = Field(default_factory=LocationData)

    @classmethod
    def from_flat_or_nested(cls, data: Optional[Dict[str, Any]] = None) -> "EnvironmentalData":
        """Instantiates EnvironmentalData from either flat or nested dictionary payloads."""
        if not data or not isinstance(data, dict):
            return cls()

        soil_keys = {"soil_ph", "soil_organic_carbon", "soil_moisture"}
        climate_keys = {"temperature", "rainfall"}
        land_keys = {"land_use", "land_cover"}
        bio_keys = {"species_richness", "habitat_diversity"}
        human_keys = {"pollution", "deforestation"}
        loc_keys = {"region", "latitude", "longitude"}

        soil_dict = dict(data.get("soil", {})) if isinstance(data.get("soil"), dict) else {}
        climate_dict = dict(data.get("climate", {})) if isinstance(data.get("climate"), dict) else {}
        land_dict = dict(data.get("land", {})) if isinstance(data.get("land"), dict) else {}
        bio_dict = dict(data.get("biodiversity", {})) if isinstance(data.get("biodiversity"), dict) else {}
        human_dict = dict(data.get("human_impact", {})) if isinstance(data.get("human_impact"), dict) else {}
        loc_dict = dict(data.get("location", {})) if isinstance(data.get("location"), dict) else {}

        # Handle crop / cropping system aliases
        for crop_key in ("crop", "crop_type", "cropping_system"):
            if crop_key in data and "land_use" not in land_dict and "land_use" not in data:
                land_dict["land_use"] = data[crop_key]

        for k, v in data.items():
            if k in soil_keys and k not in soil_dict:
                soil_dict[k] = v
            elif k in climate_keys and k not in climate_dict:
                climate_dict[k] = v
            elif k in land_keys and k not in land_dict:
                land_dict[k] = v
            elif k in bio_keys and k not in bio_dict:
                bio_dict[k] = v
            elif k in human_keys and k not in human_dict:
                human_dict[k] = v
            elif k in loc_keys and k not in loc_dict:
                loc_dict[k] = v

        return cls(
            soil=SoilData(**soil_dict),
            climate=ClimateData(**climate_dict),
            land=LandData(**land_dict),
            biodiversity=BiodiversityData(**bio_dict),
            human_impact=HumanImpactData(**human_dict),
            location=LocationData(**loc_dict),
        )

    def to_flat_dict(self) -> Dict[str, Any]:
        """Flattens all environmental attributes into a single key-value dictionary."""
        flat = {}
        for sub_model in (self.soil, self.climate, self.land, self.biodiversity, self.human_impact, self.location):
            for field_name, value in sub_model.model_dump().items():
                flat[field_name] = value
        return flat

    def get_missing_fields(self, priority_fields: Optional[List[str]] = None) -> List[str]:
        """Identifies fields that have not been provided (value is None)."""
        flat = self.to_flat_dict()
        check_list = priority_fields if priority_fields is not None else list(flat.keys())
        return [f for f in check_list if flat.get(f) is None]

    def get_provided_fields(self) -> Dict[str, Any]:
        """Returns a dictionary containing only fields with non-None values."""
        return {k: v for k, v in self.to_flat_dict().items() if v is not None}

    def completeness_score(self, target_fields: Optional[List[str]] = None) -> float:
        """Calculates completeness ratio (0.0 to 1.0) against target variables."""
        flat = self.to_flat_dict()
        targets = target_fields if target_fields is not None else list(flat.keys())
        if not targets:
            return 1.0
        provided = sum(1 for f in targets if flat.get(f) is not None)
        return round(provided / len(targets), 3)
