import os
import json
from typing import Dict, Any

class ConfigError(Exception):
    """Custom exception for configuration errors"""
    pass

class Config:
    def __init__(self):
        self._config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from config file"""
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config.json')

        if not os.path.exists(config_path):
            raise ConfigError(f"Configuration file not found at: {config_path}")

        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                return {
                    'alchemy': {
                        'api_key': config['alchemy']['api_key'],
                        'network': config['alchemy']['network'],
                        'provider_url': config['alchemy']['provider_url'],
                    },
                    'wallet': {
                        'address': config['wallet']['address'],
                        'ignored_contracts': config['wallet']['ignored_contracts'],
                    },
                    'monitoring': {
                        'block_delay': config['monitoring']['block_delay'],
                        'retry_delay': config['monitoring']['retry_delay'],
                    },
                    'debug_mode': config['debug_mode']
                }
        except KeyError as e:
            raise ConfigError(f"Missing required configuration key: {e}")
        except json.JSONDecodeError:
            raise ConfigError(f"Invalid JSON in configuration file: {config_path}")
        except Exception as e:
            raise ConfigError(f"Error loading configuration: {e}")

    @property
    def provider_url(self) -> str:
        """Get full provider URL with API key"""
        return f"{self._config['alchemy']['provider_url']}{self._config['alchemy']['api_key']}"

    @property
    def wallet_address(self) -> str:
        """Get wallet address to monitor"""
        return self._config['wallet']['address']

    @property
    def ignored_contracts(self) -> list:
        """Get list of ignored contract addresses"""
        return [addr.lower() for addr in self._config['wallet']['ignored_contracts']]

    @property
    def block_delay(self) -> int:
        """Get delay between block checks"""
        return self._config['monitoring']['block_delay']

    @property
    def retry_delay(self) -> int:
        """Get delay for retries on error"""
        return self._config['monitoring']['retry_delay']

    @property
    def debug_mode(self) -> bool:
        """Get debug mode status"""
        return self._config['debug_mode']

# Create global config instance
config = Config()