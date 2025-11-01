"""Configuration management for DDOS Tracker.

Loads configuration from config.yaml and allows environment variable overrides.
"""

import os
import yaml
from typing import Any, Dict, Optional
from pathlib import Path


# Constants
DEFAULT_CONFIG_PATH = "config.yaml"


class Config:
    """Application configuration manager.
    
    Loads configuration from YAML file and provides access with
    environment variable overrides.
    """
    
    def __init__(self, config_path: str = DEFAULT_CONFIG_PATH) -> None:
        """Initialize configuration.
        
        Args:
            config_path: Path to YAML configuration file
        """
        self.config_path = config_path
        self._config: Dict[str, Any] = {}
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from YAML file."""
        config_file = Path(self.config_path)
        
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f) or {}
        else:
            # Use defaults if config file doesn't exist
            self._config = self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration if no config file exists."""
        return {
            'app': {
                'debug': False,
                'port': 5000,
                'host': '0.0.0.0'
            },
            'security': {
                'cors_origins': ['http://localhost:3000', 'http://localhost:5000'],
                'rate_limit': {
                    'default_limits': ['200 per day', '50 per hour'],
                    'export_limit': '10 per hour',
                    'storage': 'memory://'
                }
            },
            'attack_tracking': {
                'max_attacks': 100,
                'max_threat_history': 60
            },
            'threat_scoring': {
                'score_precision': 1,
                'analysis_window_seconds': 300,
                'update_interval': 5,
                'thresholds': {
                    'critical': 80,
                    'high': 60,
                    'medium': 35
                },
                'trend_detection': {
                    'escalation_threshold': 10,
                    'de_escalation_threshold': 10
                }
            },
            'cache': {
                'duration': 90,
                'ip_geolocation_delay': 1.5
            },
            'api': {
                'max_export_limit': 1000,
                'max_filter_limit': 1000,
                'default_export_limit': 100,
                'max_time_range_minutes': 1440
            },
            'attack_generation': {
                'us_attack_probability': 0.3,
                'burst_attack_probability': 0.1,
                'ipv6_probability': 0.4,
                'intensity': {
                    'min': 0.3,
                    'max': 2.0
                },
                'sleep_time': {
                    'min': 1.0,
                    'max': 5.0
                }
            },
            'database': {
                'path': 'attacks.db'
            },
            'logging': {
                'level': 'INFO',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            }
        }
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """Get configuration value by dot-notation path.
        
        Supports environment variable overrides using DDOS_CONFIG_<PATH>.
        
        Args:
            key_path: Dot-notation path (e.g., 'app.debug')
            default: Default value if key not found
            
        Returns:
            Configuration value
            
        Examples:
            >>> config.get('app.debug')
            False
            >>> config.get('threat_scoring.thresholds.critical')
            80
        """
        # Check for environment variable override
        env_key = f"DDOS_CONFIG_{key_path.upper().replace('.', '_')}"
        env_value = os.getenv(env_key)
        if env_value is not None:
            # Try to parse as int, float, or bool
            if env_value.lower() in ('true', 'false'):
                return env_value.lower() == 'true'
            try:
                return int(env_value)
            except ValueError:
                try:
                    return float(env_value)
                except ValueError:
                    return env_value
        
        # Navigate nested dictionary
        keys = key_path.split('.')
        value = self._config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """Get entire configuration section.
        
        Args:
            section: Section name (e.g., 'security', 'app')
            
        Returns:
            Configuration section dictionary
        """
        return self._config.get(section, {})
    
    @property
    def all(self) -> Dict[str, Any]:
        """Get entire configuration dictionary."""
        return self._config


# Global configuration instance
_config: Optional[Config] = None


def get_config(config_path: str = DEFAULT_CONFIG_PATH) -> Config:
    """Get or create global configuration instance.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Configuration instance
    """
    global _config
    if _config is None:
        _config = Config(config_path)
    return _config


def reload_config(config_path: str = DEFAULT_CONFIG_PATH) -> Config:
    """Reload configuration from file.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        New configuration instance
    """
    global _config
    _config = Config(config_path)
    return _config


def load_config(config_path: str = DEFAULT_CONFIG_PATH) -> Dict[str, Any]:
    """Load configuration and return as dictionary.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Configuration dictionary
    """
    config = get_config(config_path)
    return config.all
