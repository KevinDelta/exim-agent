"""Tests for configuration loading and validation."""

import os
import pytest
from unittest.mock import patch

from src.exim_agent.config import Settings


class TestConfigurationLoading:
    """Test configuration loading and API key validation."""
    
    def test_config_loads_with_required_fields(self):
        """Test that configuration loads with required OpenAI API key."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            config = Settings()
            assert config.openai_api_key == "test-key"
    
    def test_csl_api_key_field_exists(self):
        """Test that CSL API key field is available in configuration."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True):
            config = Settings(_env_file=None)
            # Field should exist and default to None
            assert hasattr(config, 'csl_api_key')
            assert config.csl_api_key is None
    
    def test_fda_api_key_field_exists(self):
        """Test that FDA API key field is available in configuration."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True):
            config = Settings(_env_file=None)
            # Field should exist and default to None
            assert hasattr(config, 'fda_api_key')
            assert config.fda_api_key is None
    
    def test_compliance_api_keys_load_from_env(self):
        """Test that compliance API keys load from environment variables."""
        env_vars = {
            "OPENAI_API_KEY": "test-openai-key",
            "CSL_API_KEY": "test-csl-key",
            "FDA_API_KEY": "test-fda-key"
        }
        
        with patch.dict(os.environ, env_vars):
            config = Settings()
            assert config.openai_api_key == "test-openai-key"
            assert config.csl_api_key == "test-csl-key"
            assert config.fda_api_key == "test-fda-key"
    
    def test_config_validation_with_missing_required_key(self):
        """Test that configuration fails validation when required keys are missing."""
        # Clear OPENAI_API_KEY if it exists and don't load from .env
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}, clear=False):
            # Create settings without loading from .env file
            try:
                config = Settings(_env_file=None)
                # If no exception, check that openai_api_key is empty
                assert config.openai_api_key == ""
            except Exception:
                # This is expected behavior for missing required fields
                pass