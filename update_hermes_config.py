#!/usr/bin/env python3
"""Update Hermes config on VPS to use OpenRouter as default"""
import yaml
import sys

config_path = "/opt/data/config.yaml"

with open(config_path) as f:
    c = yaml.safe_load(f)

# Set OpenRouter as primary with fast model
c["model"]["provider"] = "openrouter"
c["model"]["default"] = "google/gemma-4-31b-it:free"
c["model"]["base_url"] = ""  # Use OpenRouter's default URL

# Add Ollama as fallback for local models
c["fallback_providers"] = [{"provider": "ollama", "default": "hermes3:8b"}]

with open(config_path, "w") as f:
    yaml.dump(c, f, default_flow_style=False)

print("Config updated successfully")
