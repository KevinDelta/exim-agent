# API Keys Configuration Guide

This document provides comprehensive information about configuring API keys for the Compliance Intelligence Platform.

## Overview

The platform integrates with multiple external data sources to provide real-time compliance intelligence. Each data source requires specific API credentials for authentication.

## Required Configuration

### Supabase Database
**Environment Variables:** `SUPABASE_URL`, `SUPABASE_ANON_KEY`
**Required:** Yes
**Purpose:** Database for storing compliance data

```bash
SUPABASE_URL="https://your-project.supabase.co"
SUPABASE_ANON_KEY="your-anon-key"
```

**How to set up:**
1. Visit [Supabase](https://supabase.com) and create a new project
2. Go to Settings > API to find your URL and anon key
3. Run the SQL script in `data/sql/create_compliance_table.sql` in your Supabase SQL editor
4. Add the credentials to your `.env` file

### OpenAI API Key
**Environment Variable:** `OPENAI_API_KEY`
**Required:** Yes
**Purpose:** Primary LLM provider for chat, embeddings, and memory operations

```bash
OPENAI_API_KEY="sk-proj-..."
```

**How to obtain:**
1. Visit [OpenAI Platform](https://platform.openai.com/api-keys)
2. Create a new API key
3. Copy the key and add it to your `.env` file

## Compliance Data Source API Keys

### ITA Consolidated Screening List (CSL) API
**Environment Variable:** `CSL_API_KEY`
**Required:** For real sanctions screening data
**Purpose:** Access to consolidated screening lists for sanctions compliance

```bash
CSL_API_KEY="your-csl-api-key"
```

**How to obtain:**
1. Visit [ITA Developer Portal](https://developer.trade.gov/)
2. Register for an account
3. Request access to the Consolidated Screening List API
4. Generate an API key from your dashboard

**API Documentation:** https://developer.trade.gov/consolidated-screening-list.html

### FDA Import Refusals API
**Environment Variable:** `FDA_API_KEY`
**Required:** For FDA import refusal data (if needed)
**Purpose:** Access to FDA import refusal records for food safety compliance

```bash
FDA_API_KEY="your-fda-api-key"
```

**How to obtain:**
1. Visit [FDA Open Data Portal](https://open.fda.gov/apis/)
2. Some FDA APIs may require registration
3. Check specific API documentation for authentication requirements

**Note:** Some FDA APIs are public and may not require authentication.

## Optional API Keys

### Anthropic Claude API
**Environment Variable:** `ANTHROPIC_API_KEY`
**Required:** No (alternative LLM provider)
**Purpose:** Alternative LLM provider option

```bash
ANTHROPIC_API_KEY="sk-ant-..."
```

### Groq API
**Environment Variable:** `GROQ_API_KEY`
**Required:** No (high-speed inference option)
**Purpose:** Fast inference alternative

```bash
GROQ_API_KEY="gsk_..."
```

### LangSmith Tracing
**Environment Variable:** `LANGSMITH_API_KEY`
**Required:** No (observability)
**Purpose:** LLM observability and tracing

```bash
LANGSMITH_API_KEY="lsv2_..."
LANGSMITH_PROJECT="exim-agent"
LANGSMITH_TRACING_V2=true
```

## Configuration Files

### Environment Variables (.env)
Create a `.env` file in the project root with your API keys:

```bash
# Required
SUPABASE_URL="https://your-project.supabase.co"
SUPABASE_ANON_KEY="your-anon-key"
OPENAI_API_KEY="your-openai-key"

# Compliance Data Sources (Required for real data)
CSL_API_KEY="your-csl-api-key"
FDA_API_KEY="your-fda-api-key"

# Optional
ANTHROPIC_API_KEY="your-anthropic-key"
GROQ_API_KEY="your-groq-key"
LANGSMITH_API_KEY="your-langsmith-key"
```

### Configuration Validation
Use the provided validation script to test your configuration:

```bash
python validate_config.py
```

This will check:
- ✅ All required API keys are present
- ⚠️ Optional API keys status
- 📋 Configuration summary

## Security Best Practices

### API Key Management
- **Never commit API keys to version control**
- **Use environment variables or secret management systems**
- **Rotate API keys regularly**
- **Use different keys for development and production**
- **Monitor API key usage and set up alerts**

### Environment Files
- Add `.env` to your `.gitignore` file
- Use `.env.example` as a template (without actual keys)
- Set appropriate file permissions (600) on `.env` files

### Production Deployment
- Use container secrets or cloud secret management
- Set environment variables in your deployment platform
- Never expose API keys in logs or error messages
- Implement proper error handling for authentication failures

## Troubleshooting

### Common Issues

#### Configuration Loading Errors
```bash
# Test configuration loading
python -c "from src.exim_agent.config import Settings; print('Config loaded successfully')"
```

#### API Key Validation
```bash
# Run validation script
python validate_config.py
```

#### Missing API Keys
If you see warnings about missing API keys:
- **CSL_API_KEY**: System will use mock sanctions data
- **FDA_API_KEY**: System will use mock refusal data
- This is acceptable for development and testing

### Error Messages

#### "API key not configured"
- Check that the environment variable is set correctly
- Verify the key format matches the expected pattern
- Ensure no extra spaces or quotes in the key value

#### "Authentication failed"
- Verify the API key is valid and active
- Check if the key has the required permissions
- Confirm the API endpoint is correct

## Testing Configuration

### Unit Tests
Run the configuration tests to verify setup:

```bash
python -m pytest tests/test_config.py -v
```

### Manual Validation
Use the validation script for comprehensive checking:

```bash
python validate_config.py
```

### API Connectivity Tests
Test actual API connectivity (when keys are configured):

```bash
# Test CSL API
curl -H "apikey: $CSL_API_KEY" "https://api.trade.gov/consolidated_screening_list/v1/search?name=test"

# Test FDA API (if authentication required)
curl -H "Authorization: Bearer $FDA_API_KEY" "https://api.fda.gov/food/enforcement.json?limit=1"
```

## Support

For API key issues:
- **OpenAI**: [OpenAI Support](https://help.openai.com/)
- **ITA/CSL**: [Trade Developer Support](https://developer.trade.gov/support.html)
- **FDA**: [FDA Open Data Support](https://open.fda.gov/about/)

For configuration issues:
- Check the validation script output
- Review the test results
- Consult the deployment guide for environment-specific setup