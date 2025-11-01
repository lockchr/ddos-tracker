"""Unit tests for configuration management."""

import os
import pytest
from pathlib import Path
from utils.config import Config, get_config, reload_config


class TestConfig:
    """Test suite for Config class."""
    
    def test_load_default_config(self, tmp_path):
        """Test loading default configuration when file doesn't exist."""
        config = Config(config_path=str(tmp_path / "nonexistent.yaml"))
        
        assert config.get('app.debug') == False
        assert config.get('app.port') == 5000
        assert config.get('attack_tracking.max_attacks') == 100
    
    def test_load_from_yaml(self, tmp_path):
        """Test loading configuration from YAML file."""
        # Create test config file
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text("""
app:
  debug: true
  port: 3000

security:
  cors_origins:
    - http://test.com
""")
        
        config = Config(config_path=str(config_file))
        
        assert config.get('app.debug') == True
        assert config.get('app.port') == 3000
        assert config.get('security.cors_origins') == ['http://test.com']
    
    def test_get_with_dot_notation(self, tmp_path):
        """Test accessing nested configuration with dot notation."""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text("""
threat_scoring:
  thresholds:
    critical: 90
    high: 70
""")
        
        config = Config(config_path=str(config_file))
        
        assert config.get('threat_scoring.thresholds.critical') == 90
        assert config.get('threat_scoring.thresholds.high') == 70
    
    def test_get_with_default(self):
        """Test getting configuration with default value."""
        config = Config()
        
        # Non-existent key should return default
        assert config.get('nonexistent.key', 'default_value') == 'default_value'
        
        # Existing key should return actual value
        assert config.get('app.port', 9999) == 5000
    
    def test_environment_variable_override(self, monkeypatch):
        """Test environment variable overrides."""
        config = Config()
        
        # Set environment variable
        monkeypatch.setenv('DDOS_CONFIG_APP_DEBUG', 'true')
        assert config.get('app.debug') == True
        
        monkeypatch.setenv('DDOS_CONFIG_APP_PORT', '8080')
        assert config.get('app.port') == 8080
        
        monkeypatch.setenv('DDOS_CONFIG_CACHE_DURATION', '120')
        assert config.get('cache.duration') == 120
    
    def test_get_section(self):
        """Test getting entire configuration section."""
        config = Config()
        
        app_section = config.get_section('app')
        assert isinstance(app_section, dict)
        assert 'debug' in app_section
        assert 'port' in app_section
        
        security_section = config.get_section('security')
        assert 'cors_origins' in security_section
    
    def test_all_property(self):
        """Test accessing entire configuration."""
        config = Config()
        
        all_config = config.all
        assert isinstance(all_config, dict)
        assert 'app' in all_config
        assert 'security' in all_config
        assert 'attack_tracking' in all_config
    
    def test_global_config_instance(self):
        """Test global configuration singleton."""
        config1 = get_config()
        config2 = get_config()
        
        # Should return same instance
        assert config1 is config2
    
    def test_reload_config(self, tmp_path):
        """Test reloading configuration."""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text("""
app:
  port: 3000
""")
        
        config1 = reload_config(str(config_file))
        assert config1.get('app.port') == 3000
        
        # Modify config file
        config_file.write_text("""
app:
  port: 4000
""")
        
        config2 = reload_config(str(config_file))
        assert config2.get('app.port') == 4000


class TestConfigEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_yaml_file(self, tmp_path):
        """Test handling of empty YAML file."""
        config_file = tmp_path / "empty.yaml"
        config_file.write_text("")
        
        config = Config(config_path=str(config_file))
        
        # Should fall back to defaults
        assert config.get('app.port') == 5000
    
    def test_invalid_yaml_syntax(self, tmp_path):
        """Test handling of invalid YAML syntax."""
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text("invalid: yaml: syntax:")
        
        # Should handle gracefully
        try:
            config = Config(config_path=str(config_file))
        except Exception as e:
            pytest.fail(f"Should handle invalid YAML gracefully: {e}")
    
    def test_type_conversion_from_env(self, monkeypatch):
        """Test automatic type conversion from environment variables."""
        config = Config()
        
        # Boolean conversion
        monkeypatch.setenv('DDOS_CONFIG_TEST_BOOL', 'true')
        assert config.get('test.bool') == True
        
        monkeypatch.setenv('DDOS_CONFIG_TEST_BOOL', 'false')
        assert config.get('test.bool') == False
        
        # Integer conversion
        monkeypatch.setenv('DDOS_CONFIG_TEST_INT', '42')
        assert config.get('test.int') == 42
        
        # Float conversion
        monkeypatch.setenv('DDOS_CONFIG_TEST_FLOAT', '3.14')
        assert config.get('test.float') == 3.14
        
        # String (no conversion)
        monkeypatch.setenv('DDOS_CONFIG_TEST_STRING', 'hello')
        assert config.get('test.string') == 'hello'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
