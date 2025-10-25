# Compliance Pulse - Quick Start Implementation Guide

**Ready to start?** Follow these steps to begin Phase 0 (Days 1-3)

---

## Prerequisites

✅ Current codebase with LangGraph v1 + ChromaDB + mem0 + ZenML + FastAPI
✅ Python 3.10+
✅ Environment configured (`.env` with API keys)

---

## Step 1: Create Branch

```bash
git checkout -b feature/compliance-domain-models
```

---

## Step 2: Install Additional Dependencies

Add to `pyproject.toml`:

```toml
dependencies = [
    # ... existing dependencies ...
    "httpx>=0.27.0",      # For external API calls
    "beautifulsoup4>=4.12.0",  # For HTML parsing
]
```

Then run:

```bash
uv sync
```

---

## Step 3: Create Domain Structure

Run these commands from project root:

```bash
# Create compliance domain directory
mkdir -p src/acc_llamaindex/domain/compliance
touch src/acc_llamaindex/domain/compliance/__init__.py

# Create tools directory
mkdir -p src/acc_llamaindex/domain/tools
touch src/acc_llamaindex/domain/tools/__init__.py

# Create compliance service
mkdir -p src/acc_llamaindex/application/compliance_service
touch src/acc_llamaindex/application/compliance_service/__init__.py

# Create compliance API routes
mkdir -p src/acc_llamaindex/infrastructure/api/routes
# (routes directory may already exist)

# Create compliance DB helpers
# (infrastructure/db already exists)
```

---

## Step 4: Implement Domain Models (Day 1)

### File 1: `src/acc_llamaindex/domain/compliance/enums.py`

See template in `templates/enums.py` (created below)

### File 2: `src/acc_llamaindex/domain/compliance/client_profile.py`

See template in `templates/client_profile.py` (created below)

### File 3: `src/acc_llamaindex/domain/compliance/compliance_event.py`

See template in `templates/compliance_event.py` (created below)

---

## Step 5: Write Tests

Create test file: `tests/domain/compliance/test_models.py`

```python
import pytest
from datetime import datetime
from acc_llamaindex.domain.compliance.client_profile import ClientProfile, LaneRef, SkuRef
from acc_llamaindex.domain.compliance.compliance_event import ComplianceEvent, Tile, Evidence
from acc_llamaindex.domain.compliance.enums import EventType, RiskLevel, TileStatus


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
        contact={"email": "ops@abcimports.com"},
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
    event = ComplianceEvent(
        id="evt_001",
        client_id="client_ABC",
        sku_id="SKU-123",
        lane_id="CNSHA-USLAX-ocean",
        type=EventType.SANCTIONS,
        risk_level=RiskLevel.WARN,
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
```

Run tests:

```bash
pytest tests/domain/compliance/test_models.py -v
```

---

## Step 6: Next Steps (Days 2-3)

After domain models pass tests:

1. **Day 2:** Create tools infrastructure
   - Base `ComplianceTool` class
   - Caching utilities
   - Error handling patterns

2. **Day 3:** Implement HTS Tool
   - USITC API client
   - Response parsing
   - Integration tests

See `COMPLIANCE_PULSE_IMPLEMENTATION_ROADMAP.md` for detailed daily tasks.

---

## Helpful Commands

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/acc_llamaindex/domain/compliance

# Run linting
ruff check src/

# Format code
ruff format src/

# Start API (to verify nothing broke)
fastapi dev src/acc_llamaindex/infrastructure/api/main.py
```

---

## Example: Sample Client Data (For Testing)

Create `data/sample_clients/client_ABC.json`:

```json
{
  "id": "client_ABC",
  "name": "ABC Imports Co.",
  "contact": {
    "email": "ops@abcimports.com",
    "phone": "+1-555-0100"
  },
  "lanes": [
    {
      "lane_id": "CNSHA-USLAX-ocean",
      "origin_port": "CNSHA",
      "destination_port": "USLAX",
      "mode": "ocean"
    },
    {
      "lane_id": "MXNLD-USTX-truck",
      "origin_port": "MXNLD",
      "destination_port": "USTX",
      "mode": "truck"
    }
  ],
  "watch_skus": [
    {
      "sku_id": "SKU-123",
      "description": "Cellular phones with camera",
      "hts_code": "8517.12.00",
      "origin_country": "CN",
      "lanes": ["CNSHA-USLAX-ocean"]
    },
    {
      "sku_id": "SKU-456",
      "description": "Auto parts - brake pads",
      "hts_code": "8708.30.50",
      "origin_country": "MX",
      "lanes": ["MXNLD-USTX-truck"]
    }
  ],
  "preferences": {
    "duty_delta_threshold": 0.01,
    "risk_level_filter": "warn",
    "weekly_digest_day": "sunday"
  }
}
```

---

## Template Files Location

Templates are being created in:

- `templates/domain_models/enums.py`
- `templates/domain_models/client_profile.py`
- `templates/domain_models/compliance_event.py`

Copy these to `src/acc_llamaindex/domain/compliance/` to get started.

---

## Questions or Issues?

1. Check `COMPLIANCE_PULSE_INTEGRATION_PLAN.md` for architecture details
2. Check `COMPLIANCE_PULSE_IMPLEMENTATION_ROADMAP.md` for task breakdown
3. Review existing code patterns in `src/acc_llamaindex/domain/models.py`

---

**Ready to build!** 🚀 Start with Day 1 tasks and work through the roadmap.
