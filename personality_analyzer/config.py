import json
from pathlib import Path

def load_config():
    """Load configuration from config.json in root directory"""
    config_path = Path(__file__).parent.parent / 'config.json'

    print(config_path)

    if not config_path.exists():
        raise FileNotFoundError("config.json not found in root directory")

    with open(config_path, 'r') as f:
        config = json.load(f)

    return config