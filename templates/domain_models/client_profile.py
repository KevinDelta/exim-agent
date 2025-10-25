"""Client profile domain models for compliance platform."""

from pydantic import BaseModel, Field


class LaneRef(BaseModel):
    """Reference to a logistics lane (origin-destination-mode)."""
    
    lane_id: str = Field(
        ...,
        description="Unique lane identifier (e.g., CNSHA-USLAX-ocean)",
        examples=["CNSHA-USLAX-ocean", "MXNLD-USTX-truck"]
    )
    origin_port: str = Field(
        ...,
        description="Origin port code (UN/LOCODE or similar)",
        examples=["CNSHA", "MXNLD"]
    )
    destination_port: str = Field(
        ...,
        description="Destination port code",
        examples=["USLAX", "USTX"]
    )
    mode: str = Field(
        ...,
        description="Transport mode: ocean, air, truck, or rail",
        examples=["ocean", "air", "truck", "rail"]
    )
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "lane_id": "CNSHA-USLAX-ocean",
                "origin_port": "CNSHA",
                "destination_port": "USLAX",
                "mode": "ocean"
            }
        }


class SkuRef(BaseModel):
    """Reference to a Stock Keeping Unit with compliance metadata."""
    
    sku_id: str = Field(
        ...,
        description="Unique SKU identifier",
        examples=["SKU-123", "PROD-ABC-001"]
    )
    description: str = Field(
        ...,
        description="Product description",
        examples=["Cellular phones with camera", "Auto parts - brake pads"]
    )
    hts_code: str = Field(
        ...,
        description="Harmonized Tariff Schedule code (US HTS)",
        examples=["8517.12.00", "8708.30.50"],
        pattern=r"^\d{4}\.\d{2}\.\d{2}$"
    )
    origin_country: str = Field(
        ...,
        description="ISO 2-letter country code of origin",
        examples=["CN", "MX", "VN"],
        min_length=2,
        max_length=2
    )
    lanes: list[str] = Field(
        default_factory=list,
        description="List of lane IDs this SKU travels on",
        examples=[["CNSHA-USLAX-ocean", "CNSHA-USNYC-ocean"]]
    )
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "sku_id": "SKU-123",
                "description": "Cellular phones with camera",
                "hts_code": "8517.12.00",
                "origin_country": "CN",
                "lanes": ["CNSHA-USLAX-ocean"]
            }
        }


class ClientProfile(BaseModel):
    """Client profile with watchlist of SKUs and lanes."""
    
    id: str = Field(
        ...,
        description="Unique client identifier",
        examples=["client_ABC", "org_12345"]
    )
    name: str = Field(
        ...,
        description="Client organization name",
        examples=["ABC Imports Co.", "Global Trade Partners"]
    )
    contact: dict = Field(
        ...,
        description="Contact information (email, phone, etc.)",
        examples=[{"email": "ops@abcimports.com", "phone": "+1-555-0100"}]
    )
    lanes: list[LaneRef] = Field(
        default_factory=list,
        description="List of monitored logistics lanes"
    )
    watch_skus: list[SkuRef] = Field(
        default_factory=list,
        description="List of SKUs to monitor for compliance changes"
    )
    preferences: dict = Field(
        default_factory=dict,
        description="Client-specific preferences and thresholds",
        examples=[{
            "duty_delta_threshold": 0.01,
            "risk_level_filter": "warn",
            "weekly_digest_day": "sunday"
        }]
    )
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "id": "client_ABC",
                "name": "ABC Imports Co.",
                "contact": {"email": "ops@abcimports.com"},
                "lanes": [
                    {
                        "lane_id": "CNSHA-USLAX-ocean",
                        "origin_port": "CNSHA",
                        "destination_port": "USLAX",
                        "mode": "ocean"
                    }
                ],
                "watch_skus": [
                    {
                        "sku_id": "SKU-123",
                        "description": "Cellular phones",
                        "hts_code": "8517.12.00",
                        "origin_country": "CN",
                        "lanes": ["CNSHA-USLAX-ocean"]
                    }
                ],
                "preferences": {
                    "duty_delta_threshold": 0.01
                }
            }
        }
