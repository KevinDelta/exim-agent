import pytest
from datetime import datetime
from exim_agent.domain.compliance.client_profile import ClientProfile, LaneRef, SkuRef
from exim_agent.domain.compliance.compliance_event import ComplianceEvent, Tile, Evidence
from exim_agent.domain.compliance.enums import EventType, RiskLevel, TileStatus


def test_lane_ref_creation():
    """Test LaneRef model creation."""
    lane = LaneRef(
        lane_id="CNSHA-USLAX-ocean",
        origin_port="CNSHA",
        destination_port="USLAX",
        mode="ocean"
    )
    assert lane.lane_id == "CNSHA-USLAX-ocean"
    assert lane.mode == "ocean"


def test_sku_ref_creation():
    """Test SkuRef model creation."""
    sku = SkuRef(
        sku_id="SKU-123",
        description="Cellular phones",
        hts_code="8517.12.00",
        origin_country="CN",
        lanes=["CNSHA-USLAX-ocean"]
    )
    assert sku.sku_id == "SKU-123"
    assert sku.hts_code == "8517.12.00"


def test_client_profile_creation():
    """Test ClientProfile model creation."""
    client = ClientProfile(
        id="client_ABC",
        name="ABC Imports",
        contact_email="ops@abcimports.com",
        lanes=[
            LaneRef(
                lane_id="CNSHA-USLAX-ocean",
                origin_port="CNSHA",
                destination_port="USLAX",
                mode="ocean"
            )
        ],
        watch_skus=[
            SkuRef(
                sku_id="SKU-123",
                description="Cellular phones",
                hts_code="8517.12.00",
                origin_country="CN",
                lanes=["CNSHA-USLAX-ocean"]
            )
        ]
    )
    assert client.id == "client_ABC"
    assert len(client.watch_skus) == 1


def test_compliance_event_creation():
    """Test ComplianceEvent model creation."""
    from exim_agent.domain.compliance.enums import ComplianceArea
    
    event = ComplianceEvent(
        id="evt_001",
        client_id="client_ABC",
        sku_id="SKU-123",
        lane_id="CNSHA-USLAX-ocean",
        type=EventType.SANCTIONS,
        compliance_area=ComplianceArea.SANCTIONS_SCREENING,
        risk_level=RiskLevel.WARN,
        title="New OFAC Sanctions Alert",
        summary_md="New entity added to OFAC list",
        evidence=[
            Evidence(
                source="OFAC CSL",
                url="https://api.trade.gov/...",
                snippet="Shanghai Telecom added 2025-01-15",
                last_updated="2025-01-15T10:00:00Z"
            )
        ]
    )
    assert event.type == EventType.SANCTIONS
    assert event.risk_level == RiskLevel.WARN
    assert len(event.evidence) == 1


def test_tile_creation():
    """Test Tile model creation."""
    tile = Tile(
        status=TileStatus.ATTENTION,
        headline="New Sanctions Alert",
        details_md="**Shanghai Telecom** added to Entity List"
    )
    assert tile.status == TileStatus.ATTENTION
    assert "Shanghai Telecom" in tile.details_md