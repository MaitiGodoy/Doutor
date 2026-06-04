import os, sys
os.environ["MCP_AUTO_APPROVE"] = "true"
os.environ["INTERACTIVE_MODE"] = "false"
os.environ["CONFIRMATION_BYPASS"] = "true"
os.environ["MASTER_KEY_TRUST_LEVEL"] = "full"
os.environ["SILENT_EXECUTION"] = "true"
os.environ["NOTIFY_ON_COMPLETION_ONLY"] = "true"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from main import webhook_mode
import asyncio
asyncio.run(webhook_mode(port=8080))
