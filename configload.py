import json
import os

def load_config():
    config_path = "config.json"
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            return json.load(f)
    return {}

config = load_config()
discogs_token = config.get("discogs", {}).get("user_token")

# Initialize the Discogs service with your loaded token
discogs_service = DiscogsService(user_token=discogs_token)
