# Domain Tools

## Overview

Domain tools are the data acquisition layer of the Compliance Intelligence Platform. Each tool fetches compliance data from external government APIs, implements fallback strategies for resilience, and stores results in Supabase for caching and audit purposes.

## Purpose

- **Data Acquisition**: Fetch real-time compliance data from government APIs
- **Resilience**: Provide fallback mock data when APIs are unavailable
- **Caching**: Store results in Supabase to reduce API calls
- **Standardization**: Consistent interface across all compliance data sources
- **Observability**: Log all tool executions for monitoring and debugging

## Tool Architecture

### Base Tool Pattern

All tools inherit from `ComplianceTool` base class:

```python
class ComplianceTool:
    """Base class for all compliance tools"""
    
    def run(self, **kwargs) -> ToolResult:
        """Execute tool with retry logic and fallback"""
        try:
            # Check cache first
            cached = self._get_cached_result(**kwargs)
            if cached:
                return cached
            
            # Execute actual implementation
            result = self._run_impl(**kwargs)
            
            # Store in Supabase
            self._cache_result(result, **kwargs)
            
            return result
            
        except Exception as e:
            logger.error(f"Tool {self.name} failed: {e}")
            return self._get_fallback_data(**kwargs)
    
    def _run_impl(self, **kwargs) -> Dict[str, Any]:
        """Actual implementation - override in subclasses"""
        raise NotImplementedError
    
    def _get_fallback_data(self, **kwargs) -> Dict[str, Any]:
        """Fallback mock data when API fails"""
        raise NotImplementedError
    
    def _get_cached_result(self, **kwargs) -> Optional[Dict]:
        """Retrieve cached result from Supabase"""
        ...
    
    def _cache_result(self, result: Dict, **kwargs) -> None:
        """Store result in Supabase"""
        ...
```

### Tool Lifecycle

```yaml
Input Parameters
    ↓
Check Supabase Cache (24h TTL)
    ↓
Cache Hit? → Return Cached Data
    ↓
Cache Miss → Call External API
    ↓
API Success? → Store in Supabase → Return Data
    ↓
API Failure → Log Error → Return Fallback Data
```

## Available Tools

### 1. HTS Tool (`hts_tool.py`)

**Purpose**: Fetch Harmonized Tariff Schedule classification and duty rates

**API**: USITC HTS Database

- Endpoint: `https://hts.usitc.gov/api/`
- Authentication: Public API (no key required)
- Rate Limit: 100 requests/minute

**Input Parameters**:

```python
{
    "hts_code": "8471.30.01",  # 10-digit HTS code
    "lane_id": "US-CN"         # Trade route (optional)
}
```

**Output**:

```json
{
    "success": True,
    "hts_code": "8471.30.01",
    "description": "Portable automatic data processing machines, weighing not more than 10 kg",
    "duty_rate": "0%",
    "unit": "No.",
    "special_rates": {
        "MFN": "0%",
        "China": "0%"
    },
    "source_url": "https://hts.usitc.gov/view/...",
    "last_updated": "2024-01-15T10:30:00Z"
}
```

**Fallback Data**: Common HTS codes with typical duty rates

**Use Cases**:

- Tariff classification verification
- Duty rate calculation
- Trade agreement eligibility

### 2. Sanctions Tool (`sanctions_tool.py`)

**Purpose**: Screen parties against consolidated sanctions lists

**API**: ITA Consolidated Screening List (CSL)

- Endpoint: `https://api.trade.gov/consolidated_screening_list/search`
- Authentication: API key required (`CSL_API_KEY`)
- Rate Limit: 1000 requests/hour

**Input Parameters**:

```python
{
    "party_name": "Acme Trading Co",  # Company or individual name
    "country": "CN",                   # ISO country code (optional)
    "lane_id": "US-CN"                 # Trade route (optional)
}
```

**Output**:

```json
{
    "success": True,
    "matches_found": True,
    "match_count": 2,
    "matches": [
        {
            "name": "Acme Trading Co Ltd",
            "country": "CN",
            "list": "Entity List",
            "programs": ["Export Control"],
            "match_score": 0.95,
            "source_url": "https://..."
        }
    ],
    "risk_assessment": "high",  # high/medium/low
    "recommendation": "Block transaction - Entity List match",
    "last_updated": "2024-01-15T10:30:00Z"
}
```

**Fallback Data**: Empty sanctions list (no matches)

**Use Cases**:

- Pre-transaction screening
- Supplier due diligence
- Export control compliance

### 3. Refusals Tool (`refusals_tool.py`)

**Purpose**: Query FDA/FSIS import refusal databases

**APIs**:

- FDA Import Refusals: `https://www.accessdata.fda.gov/scripts/importrefusals/`
- FSIS Import Refusals: `https://www.fsis.usda.gov/inspection/import-export/`

**Input Parameters**:

```json
{
    "hts_code": "0201.10.00",      # HTS code for product
    "product_description": "Beef",  # Product description (optional)
    "country": "BR",                # Origin country (optional)
    "lane_id": "US-BR"              # Trade route (optional)
}
```

**Output**:

```json
{
    "success": True,
    "total_refusals": 45,
    "recent_refusals": [
        {
            "date": "2024-01-10",
            "product": "Fresh beef",
            "country": "Brazil",
            "reason": "Salmonella",
            "fda_sample_number": "12345",
            "hts_code": "0201.10.00"
        }
    ],
    "refusal_reasons": {
        "Salmonella": 30,
        "Listeria": 10,
        "Veterinary Drug Residue": 5
    },
    "risk_level": "high",  # high/medium/low
    "trend": "increasing",  # increasing/stable/decreasing
    "last_updated": "2024-01-15T10:30:00Z"
}
```

**Fallback Data**: Empty refusal list (no recent refusals)

**Use Cases**:

- Food safety risk assessment
- Supplier quality monitoring
- Import planning

### 4. Rulings Tool (`rulings_tool.py`)

**Purpose**: Retrieve CBP customs rulings and interpretations

**API**: CBP CROSS (Customs Rulings Online Search System)

- Endpoint: `https://rulings.cbp.gov/api/`
- Authentication: Public API (no key required)
- Rate Limit: 50 requests/minute

**Input Parameters**:

```json
{
    "hts_code": "8471.30.01",      # HTS code
    "keywords": "laptop computer",  # Search keywords (optional)
    "ruling_number": "N123456",     # Specific ruling (optional)
    "lane_id": "US-CN"              # Trade route (optional)
}
```

**Output**:

```json
{
    "success": True,
    "total_rulings": 12,
    "relevant_rulings": [
        {
            "ruling_number": "N123456",
            "issue_date": "2023-11-15",
            "hts_code": "8471.30.01",
            "description": "Classification of portable computers",
            "summary": "Portable computers with integrated display...",
            "ruling_url": "https://rulings.cbp.gov/...",
            "relevance_score": 0.92
        }
    ],
    "key_findings": [
        "Integrated display required for HTS 8471.30.01",
        "Weight limit of 10kg applies"
    ],
    "last_updated": "2024-01-15T10:30:00Z"
}
```

**Fallback Data**: Generic rulings for common HTS codes

**Use Cases**:

- Classification guidance
- Valuation disputes
- Country of origin determinations

## Tool Integration

### Parallel Execution

Tools are designed for parallel execution in the Compliance Graph:

```json
{
  "tools": ["hts_tool", "sanctions_tool", "refusals_tool", "rulings_tool"],
  "execution_mode": "parallel",
  "concurrency_limit": 4
}
```

```python
import asyncio

async def execute_tools_parallel(sku_id: str, lane_id: str, hts_code: str):
    """Execute all tools in parallel"""
    
    tasks = [
        hts_tool.run_async(hts_code=hts_code, lane_id=lane_id),
        sanctions_tool.run_async(party_name=sku_id, lane_id=lane_id),
        refusals_tool.run_async(hts_code=hts_code, lane_id=lane_id),
        rulings_tool.run_async(hts_code=hts_code, lane_id=lane_id)
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    return {
        "hts": results[0],
        "sanctions": results[1],
        "refusals": results[2],
        "rulings": results[3]
    }
```

### HTTP Client Pooling

Tools share a connection pool for efficiency:

```python
from exim_agent.infrastructure.http_client import get_shared_client

class ComplianceTool:
    def __init__(self):
        self.http_client = get_shared_client()
        # Reuses connections across tools
        # Max 100 connections, max 10 per host
```

### Retry Logic

Built-in exponential backoff for transient failures:

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((ConnectionError, Timeout))
)
def _call_api(self, url: str, params: Dict) -> Dict:
    response = self.http_client.get(url, params=params, timeout=10)
    response.raise_for_status()
    return response.json()
```

## Caching Strategy

### Supabase Cache

Results stored in `compliance_data` table:

```sql
CREATE TABLE compliance_data (
    id UUID PRIMARY KEY,
    source_type TEXT NOT NULL,  -- 'hts', 'sanctions', 'refusals', 'rulings'
    source_id TEXT NOT NULL,    -- hts_code, party_name, etc.
    data JSONB NOT NULL,
    content_hash TEXT,          -- For change detection
    last_crawled_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(source_type, source_id)
);
```

### Cache TTL

- **HTS Data**: 24 hours (tariff rates change infrequently)
- **Sanctions Data**: 1 hour (high-priority, frequent updates)
- **Refusals Data**: 6 hours (moderate update frequency)
- **Rulings Data**: 7 days (rulings are historical)

### Cache Invalidation

```python
# Force fresh data (bypass cache)
result = tool.run(hts_code="1234.56.78", force_refresh=True)

# Clear cache for specific key
tool.clear_cache(hts_code="1234.56.78")

# Clear all cache for tool
tool.clear_all_cache()
```

## Fallback Strategy

### When Fallback is Used

1. **API Unavailable**: Network errors, timeouts, 5xx errors
2. **Rate Limit Exceeded**: 429 Too Many Requests
3. **Authentication Failure**: Invalid or expired API keys
4. **Invalid Response**: Malformed JSON, unexpected schema
5. **Timeout**: Request exceeds configured timeout (10s)

### Fallback Data Quality

- **Realistic**: Based on common real-world scenarios
- **Consistent**: Same input always returns same fallback
- **Marked**: Includes `is_fallback: true` flag
- **Logged**: All fallback usage logged for monitoring

### Example Fallback

```python
def _get_fallback_data(self, hts_code: str, **kwargs) -> Dict:
    """Fallback HTS data for common codes"""
    
    fallback_db = {
        "8471.30.01": {
            "description": "Portable computers",
            "duty_rate": "0%",
            "unit": "No."
        },
        # ... more common codes
    }
    
    return {
        "success": True,
        "is_fallback": True,
        "hts_code": hts_code,
        **fallback_db.get(hts_code, {
            "description": "Unknown product",
            "duty_rate": "Unknown",
            "unit": "Unknown"
        }),
        "warning": "Using fallback data - API unavailable"
    }
```

## Error Handling

### Error Types

```python
class ToolError(Exception):
    """Base exception for tool errors"""
    pass

class APIError(ToolError):
    """External API returned error"""
    pass

class CacheError(ToolError):
    """Cache read/write failed"""
    pass

class ValidationError(ToolError):
    """Input validation failed"""
    pass
```

### Error Logging

```python
logger.error(
    "Tool execution failed",
    extra={
        "tool_name": "HTSTool",
        "hts_code": "1234.56.78",
        "error_type": "APIError",
        "error_message": str(e),
        "fallback_used": True,
        "correlation_id": "pulse_123"
    }
)
```

## Performance Characteristics

### Latency

- **Cache Hit**: <50ms (Supabase query)
- **API Call**: 500ms - 2s (external API)
- **Fallback**: <10ms (in-memory data)
- **Parallel Execution**: 60-70% faster than sequential

### Throughput

- **Sequential**: ~10 SKU+Lanes per minute
- **Parallel (4 tools)**: ~30 SKU+Lanes per minute
- **With Caching**: ~100 SKU+Lanes per minute

### Resource Usage

- **Memory**: ~50MB per tool instance
- **Connections**: Shared pool (max 100 total)
- **CPU**: Minimal (I/O bound operations)

## Configuration

### Environment Variables

```bash
# API Keys
CSL_API_KEY=xxx  # ITA Consolidated Screening List (required)

# Supabase (for caching)
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=xxx

# Performance Tuning
TOOL_TIMEOUT_SECONDS=10
TOOL_RETRY_ATTEMPTS=3
TOOL_CACHE_TTL_HOURS=24
HTTP_MAX_CONNECTIONS=100
HTTP_MAX_KEEPALIVE_CONNECTIONS=20
```

### Tool Configuration

```python
# In config.py
class ToolConfig:
    timeout: int = 10  # seconds
    retry_attempts: int = 3
    cache_ttl: int = 24  # hours
    enable_fallback: bool = True
    log_level: str = "INFO"
```

## Testing

### Unit Tests

```bash
# Test individual tools with mocked HTTP
pytest tests/test_hts_tool.py -v
pytest tests/test_sanctions_tool.py -v
pytest tests/test_refusals_tool.py -v
pytest tests/test_rulings_tool.py -v
```

### Integration Tests

```bash
# Test with real APIs (requires API keys)
pytest tests/test_compliance_tools.py -v --integration
```

### Fallback Tests

```bash
# Test fallback behavior
pytest tests/test_tool_fallback.py -v
```

## Monitoring

### Metrics to Track

- **API Success Rate**: Percentage of successful API calls
- **Cache Hit Rate**: Percentage of cache hits vs misses
- **Fallback Usage**: Frequency of fallback data usage
- **Response Time**: P50, P95, P99 latencies
- **Error Rate**: Errors per tool per hour

### Alerts

- API success rate < 90% for 5 minutes
- Fallback usage > 20% for 10 minutes
- Response time P95 > 5 seconds
- Cache hit rate < 50% (indicates cache issues)

## Best Practices

### For Developers

1. **Always Handle Failures**: Never assume API calls succeed
2. **Use Async Methods**: Leverage parallel execution for performance
3. **Respect Rate Limits**: Implement backoff and retry logic
4. **Cache Aggressively**: Reduce API calls and improve latency
5. **Log Everything**: Include context for debugging

### For Operators

1. **Monitor API Keys**: Rotate regularly, track usage
2. **Watch Rate Limits**: Adjust request frequency if needed
3. **Review Fallback Usage**: High usage indicates API issues
4. **Optimize Cache TTL**: Balance freshness vs performance
5. **Test Fallback Data**: Ensure quality and accuracy

## Future Enhancements

- [ ] GraphQL API support for more efficient queries
- [ ] Webhook subscriptions for real-time updates
- [ ] Machine learning for intelligent caching
- [ ] Predictive prefetching based on usage patterns
- [ ] Multi-region API failover
- [ ] Advanced rate limit management
- [ ] Tool result versioning and history

## Related Documentation

- [Compliance Service README](../../application/compliance_service/README.md) - Tool orchestration
- [Database README](../../infrastructure/db/README.md) - Caching and storage
- [HTTP Client Pooling](../../../docs/HTTP_CLIENT_POOLING.md) - Connection management
